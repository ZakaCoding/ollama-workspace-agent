from copy import deepcopy
from types import SimpleNamespace

import pytest

from app.agent import core
from app.agent.context import ContextBuilder
from app.agent.verifier import has_repeated_blocks
from app.llm.client import IncompleteResponseError, LLMClient


def response(content):
    return {'choices': [{'message': {'content': content}}]}


@pytest.mark.parametrize('task', [
    'did u have problem', 'Do you have any problems?', 'Are u having a problem?',
    'are you working?', 'why are you not responding?', "why can't you reply?",
    'what can you do?', 'how are you?', 'are you there?',
])
@pytest.mark.parametrize('streaming', [False, True])
def test_assistant_questions_are_isolated_conversation(monkeypatch, task, streaming):
    agent = core.Agent()
    agent.messages += [{'role': 'user', 'content': 'Fix calculator.py'},
                       {'role': 'assistant', 'content': 'Let me run the tests.'}]
    def check(messages):
        assert len(messages) == 2
        assert messages[-1]['content'] == task
        assert 'calculator.py' not in str(messages)
    def chat(messages, tools=None):
        check(messages)
        assert tools == []
        return response('I can reply now. What happened?')
    def stream(messages):
        check(messages)
        yield 'I can reply now. What happened?'
    monkeypatch.setattr(agent.llm, 'chat', chat)
    monkeypatch.setattr(agent.llm, 'chat_stream', stream)
    assert not core.task_requires_code_search(task)
    answer = ''.join(agent.stream(task)) if streaming else agent.run(task)
    assert answer == 'I can reply now. What happened?'
    assert agent.state.completed
    assert not agent.state.tool_calls


@pytest.mark.parametrize('task', [
    'Do you have any problems in calculator.py?', 'Are you working? Read app.py.',
    'Can you respond by fixing app.py?', 'How are you handling errors in this repository?',
])
def test_repository_work_is_not_misclassified_as_assistant_health(task):
    assert not core.task_is_conversational(task)


def test_repeated_code_and_prose_is_rejected_on_nonretrieval_route(monkeypatch):
    agent = core.Agent()
    loop = ('Let me read calculator.py to verify the current implementation:\n\n'
            '```python\nwith open("calculator.py") as source:\n    print(source.read())\n```\n\n') * 5
    assert has_repeated_blocks(loop)
    monkeypatch.setattr(agent.llm, 'chat', lambda **kwargs: response(loop))
    answer = agent.run('inspect files')
    assert answer == core.INVALID_RESPONSE_MESSAGE
    assert not agent.state.completed
    assert agent.state.errors


def test_nonretrieval_narration_retries_and_accepts_clean_answer(monkeypatch):
    agent = core.Agent()
    answers = iter([response('Let me read calculator.py.'), response('I can reply now.')])
    monkeypatch.setattr(agent.llm, 'chat', lambda **kwargs: next(answers))
    assert agent.run('did u have problem') == 'I can reply now.'
    assert agent.state.completed
    assert agent.state.tool_calls == 0


def test_stream_retry_goes_through_guard_and_saves_completion(monkeypatch):
    agent = core.Agent()
    streams = iter(['', 'Let me run the tests.'])
    monkeypatch.setattr(agent.llm, 'chat_stream', lambda messages: iter([next(streams)]))
    monkeypatch.setattr(agent.llm, 'chat', lambda **kwargs: response('I can reply now.'))
    assert ''.join(agent.stream('did u have problem')) == 'I can reply now.'
    assert agent.state.completed
    assert agent.messages[-1]['content'] == 'I can reply now.'


def test_repeated_short_code_lines_are_not_a_response_loop():
    assert not has_repeated_blocks('```python\n' + '\n\n'.join(['    pass'] * 8) + '\n```')


def test_tool_budget_bounds_large_current_turn_without_losing_call_ids():
    builder = ContextBuilder(model_context_tokens=4096)
    messages = [{'role': 'system', 'content': 'Repository evidence for the requested change: stale'},
                {'role': 'user', 'content': 'inspect files'}]
    for i in range(6):
        name = 'run_command' if i == 5 else 'read_file'
        messages += [
            {'role': 'assistant', 'content': None, 'tool_calls': [
                {'id': str(i), 'function': {'name': name, 'arguments': '{}'}}]},
            {'role': 'tool', 'tool_call_id': str(i),
             'content': ('unrelated source\n' * 5000) + '\nEXIT_CODE=1'},
        ]
    original = deepcopy(messages)
    bounded = builder.bound_tool_messages(messages, 'inspect files')
    assert sum(len(m['content']) for m in bounded if m['role'] == 'tool') <= builder.max_chars
    assert [m['tool_call_id'] for m in bounded if m['role'] == 'tool'] == [str(i) for i in range(6)]
    assert bounded[-1]['content'].endswith('EXIT_CODE=1')
    assert messages == original
    assert not any('stale' in (m.get('content') or '') for m in bounded)


def test_search_tool_compresses_legacy_oversized_chunks(tmp_path, monkeypatch):
    from app.tools import search as module
    (tmp_path / '.owa').mkdir()
    (tmp_path / '.owa/index.db').touch()
    monkeypatch.setattr(module, 'current_workspace', lambda: tmp_path)
    monkeypatch.setattr(module, 'search', lambda *args: [
        {'path': 'worker.py', 'chunk_index': 0, 'score': 0.9,
         'content': '# background\n' * 5000 + 'def retry_request():\n    return True\n'},
    ])
    output = module.search_code('retry_request', limit=10)
    assert len(output) <= ContextBuilder().max_chars
    assert 'def retry_request' in output
    assert '[worker.py#chunk=0]' in output
    assert '[excerpt omitted]' in output


def test_large_tool_result_is_verified_before_prompt_and_history_compression(monkeypatch):
    agent = core.Agent()
    answers = iter([
        {'choices': [{'message': {'content': None, 'tool_calls': [
            {'id': 'r', 'function': {'name': 'run_command', 'arguments': '{"command":"pytest"}'}}
        ]}}]}, response('Tests passed.'),
    ])
    def chat(messages, tools=None):
        for m in messages:
            if m['role'] == 'tool':
                assert len(m['content']) <= agent.context_builder.max_chunk_chars
                assert m['content'].endswith('EXIT_CODE=0')
        return next(answers)
    monkeypatch.setattr(agent.llm, 'chat', chat)
    monkeypatch.setitem(core.FUNCTIONS, 'run_command', lambda **kwargs: 'test output\n' * 10000 + 'EXIT_CODE=0')
    assert agent.run('Run pytest') == 'Tests passed.'
    assert agent.state.verification_done
    assert max(len(m.get('content') or '') for m in agent.messages if m['role'] == 'tool') <= 3000


@pytest.mark.parametrize('finish_reason', ['length', 'content_filter'])
def test_nonstreaming_truncation_is_not_accepted_or_executed(finish_reason):
    client = LLMClient()
    fake = SimpleNamespace(
        raise_for_status=lambda: None,
        json=lambda: {'choices': [{'finish_reason': finish_reason,
                                  'message': {'content': 'partial'}}]},
    )
    client.session = SimpleNamespace(post=lambda *args, **kwargs: fake)
    with pytest.raises(IncompleteResponseError):
        client.chat([{'role': 'user', 'content': 'inspect files'}])
    assert client.metrics.snapshot()['failed_requests'] == 1


def test_cut_short_action_response_is_explicit_and_incomplete(monkeypatch):
    agent = core.Agent()
    def truncated(**kwargs):
        raise IncompleteResponseError('Model response ended with finish reason: length')
    monkeypatch.setattr(agent.llm, 'chat', truncated)
    assert ''.join(agent.stream('inspect files')) == core.INCOMPLETE_RESPONSE_MESSAGE
    assert not agent.state.completed
    assert not agent.state.tool_calls


def test_empty_sync_answer_is_not_marked_complete(monkeypatch):
    agent = core.Agent()
    monkeypatch.setattr(agent.llm, 'chat', lambda **kwargs: response(''))
    assert agent.run('hello') == core.NO_RESPONSE_MESSAGE
    assert not agent.state.completed


def test_quoted_source_narration_is_not_treated_as_an_action():
    from app.agent.verifier import detect_fake_narration
    content = ('The source contains this example:\n\n'
               '```python\nprint("Let me read the file.")\n```\n\n'
               '> Let me run the tests.\n\n'
               'The phrase `I will execute the command` is sample text.')
    assert detect_fake_narration(content).passed
    assert not detect_fake_narration('Let me read the file.\n\n' + content).passed


def test_search_headers_and_tail_match_survive_tool_budget(monkeypatch, tmp_path):
    from app.tools import search as module
    (tmp_path / '.owa').mkdir()
    (tmp_path / '.owa/index.db').touch()
    monkeypatch.setattr(module, 'current_workspace', lambda: tmp_path)
    monkeypatch.setattr(module, 'search', lambda *args: [
        {'path': 'worker.py', 'chunk_index': 0, 'score': 1,
         'content': '# irrelevant background\n' * 3000 + "def retry_request():\n    return 'retry accepted'\n"},
    ])
    result = module.search_code('retry_request')
    assert result.startswith('Found 1 source chunk(s).')
    assert len(result) <= 3000
    builder = ContextBuilder(model_context_tokens=4096)
    messages = [{'role': 'assistant', 'tool_calls': [
        {'id': 's', 'function': {'name': 'search_code', 'arguments': '{}'}}]},
        {'role': 'tool', 'tool_call_id': 's', 'content': result}]
    bounded = builder.bound_tool_messages(messages, 'find retry_request')[-1]['content']
    assert '[worker.py#chunk=0]' in bounded
    assert 'FILE: worker.py' in bounded
    assert "return 'retry accepted'" in bounded


@pytest.mark.parametrize('task', ['hi then', 'Hey there!', 'hello owa', 'okay, hi again', 'bye then'])
@pytest.mark.parametrize('streaming', [False, True])
def test_greeting_variations_do_not_resume_repository_discussion(monkeypatch, task, streaming):
    test_assistant_questions_are_isolated_conversation(monkeypatch, task, streaming)


def test_greeting_before_an_explicit_edit_retains_edit_intent():
    task = 'Hi, can you fix calculator.py?'
    assert not core.task_is_conversational(task)
    assert not core.task_is_read_only(task)
    assert 'patch_file' in {t['function']['name'] for t in core._tools_for_task(False, False, task)}
