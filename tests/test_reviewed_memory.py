"""Dependency-free storage regressions plus agent integration when installed."""
import contextlib
import io
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.memory.lessons import LessonStore
from app.memory.__main__ import main


class LessonTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = LessonStore(self.root)

    def test_empty_recall_does_not_create_database(self):
        self.assertEqual(self.store.context(), '')
        self.assertFalse(self.store.path.exists())

    def test_pending_is_not_recalled(self):
        self.store.propose('Run tests', 'task 1')
        self.assertEqual(self.store.context(), '')

    def test_approval_persists_across_instances(self):
        lesson = self.store.propose('Run tests', 'commit abc')
        self.store.review(lesson, 'approved')
        restored = LessonStore(self.root)
        self.assertIn('Run tests', restored.context())
        self.assertIn('commit abc', restored.context())
        self.assertIsNotNone(restored.list()[0]['reviewed_at'])

    def test_revoked_and_rejected_are_not_recalled(self):
        for decision in ['rejected', 'revoked']:
            lesson = self.store.propose(decision, 'task 1')
            if decision == 'revoked':
                self.store.review(lesson, 'approved')
            self.store.review(lesson, decision)
        self.assertEqual(self.store.context(), '')

    def test_invalid_transitions_fail_closed(self):
        lesson = self.store.propose('Run tests', 'task 1')
        with self.assertRaises(ValueError):
            self.store.review(lesson, 'revoked')
        self.store.review(lesson, 'rejected')
        with self.assertRaises(ValueError):
            self.store.review(lesson, 'approved')
        with self.assertRaises(ValueError):
            self.store.review(999, 'approved')

    def test_copied_database_cannot_recall_or_review_other_workspace(self):
        lesson = self.store.propose('private project detail', 'task 1')
        self.store.review(lesson, 'approved')
        other = LessonStore(self.root / 'other')
        other.path.parent.mkdir(parents=True)
        shutil.copy2(self.store.path, other.path)
        self.assertEqual(other.list(), [])
        self.assertEqual(other.context(), '')
        with self.assertRaises(ValueError):
            other.review(lesson, 'revoked')

    def test_state_directory_symlink_rejected(self):
        target = self.root / 'shared'
        target.mkdir()
        self.store.path.parent.symlink_to(target, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.store.propose('unsafe shared state', 'task 1')

    def test_database_symlink_rejected(self):
        self.store.propose('test', 'task 1')
        other = self.root / 'copy.db'
        self.store.path.rename(other)
        self.store.path.symlink_to(other)
        with self.assertRaises(ValueError):
            self.store.context()

    def test_bounds_and_provenance_required(self):
        for content, source in [('', 'task'), ('x' * 1001, 'task'), ('ok', ''), ('ok', 's' * 501)]:
            with self.assertRaises(ValueError):
                self.store.propose(content, source)
        with self.assertRaises(ValueError):
            self.store.list(limit=-1)

    def test_recall_is_bounded_to_three_latest_approved(self):
        for number in range(5):
            lesson = self.store.propose(f'lesson {number}', 'task 1')
            self.store.review(lesson, 'approved')
        context = self.store.context()
        self.assertNotIn('lesson 0', context)
        self.assertNotIn('lesson 1', context)
        self.assertIn('lesson 4', context)

    def test_long_lessons_keep_valid_bounded_json(self):
        import json
        for _ in range(3):
            self.store.review(self.store.propose('x' * 1000, 's' * 500), 'approved')
        content = self.store.context()
        self.assertLessEqual(len(content), 2500)
        self.assertEqual(len(json.loads(content.split('\n', 1)[1])), 1)

    def test_cli_review_flow(self):
        args = ['--workspace', str(self.root)]
        with contextlib.redirect_stdout(io.StringIO()):
            main(args + ['propose', 'run regression', '--source', 'task 1'])
            main(args + ['approve', '1'])
        self.assertIn('run regression', self.store.context())
        with contextlib.redirect_stdout(io.StringIO()):
            main(args + ['revoke', '1'])
        self.assertEqual(self.store.context(), '')


try:
    from app.agent import core
except ModuleNotFoundError as exc:
    if exc.name not in {"rich", "dotenv", "requests", "httpx"}:
        raise
    core = None


@unittest.skipIf(core is None, 'Agent runtime dependencies are not installed')
class AgentLessonTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = LessonStore(self.root)
        self.agent = core.Agent.__new__(core.Agent)
        self.agent.messages = [{'role': 'system', 'content': 'base'}, {'role': 'user', 'content': 'fix bug'}]
        from types import SimpleNamespace
        self.agent.context_builder = SimpleNamespace(bound_tool_messages=lambda messages, task: messages)
        self.addCleanup(patch.stopall)
        patch.object(core, 'current_workspace', return_value=self.root).start()
        patch.object(core, 'task_is_conversational', return_value=False).start()
        patch.object(core, 'task_requires_code_search', return_value=False).start()

    def test_recall_disabled_by_default(self):
        self.store.review(self.store.propose('unique lesson', 'task 1'), 'approved')
        with patch.dict('os.environ', {'OWA_LESSON_MEMORY': '0'}):
            self.assertEqual(self.agent._request_messages('fix bug'), self.agent.messages)

    def test_recall_does_not_persist_and_revocation_refreshes(self):
        lesson = self.store.propose('unique lesson', 'task 1')
        self.store.review(lesson, 'approved')
        with patch.dict('os.environ', {'OWA_LESSON_MEMORY': '1'}):
            messages = self.agent._request_messages('fix bug')
            recalled = [m for m in messages if 'unique lesson' in m.get('content', '')]
            self.assertEqual(len(recalled), 1)
            self.assertEqual(recalled[0]['role'], 'user')
            self.assertNotIn('unique lesson', str(self.agent.messages))
            self.store.review(lesson, 'revoked')
            self.assertNotIn('unique lesson', str(self.agent._request_messages('fix bug')))

    def test_corrupt_database_does_not_block_request(self):
        self.store.path.parent.mkdir()
        self.store.path.write_bytes(b'not sqlite')
        with patch.dict('os.environ', {'OWA_LESSON_MEMORY': '1'}):
            self.assertEqual(self.agent._request_messages('fix bug'), self.agent.messages)


if __name__ == '__main__':
    unittest.main()
