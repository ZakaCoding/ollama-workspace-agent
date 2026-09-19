from app.agent.verifier import detect_unsupported_claims
from app.agent.core import Agent, _REFUSE_MESSAGE


EVIDENCE = """REPOSITORY CONTEXT
==================

EVIDENCE: [app/indexer/search.py#chunk=0]
FILE: app/indexer/search.py
CONTENT:
def search(query):
    return keyword_similarity(query)
"""


def test_supported_citation_claim_passes():
    result = detect_unsupported_claims(
        "The search function uses keyword similarity [app/indexer/search.py#chunk=0].",
        EVIDENCE,
    )

    assert result.passed


def test_valid_citation_does_not_make_unrelated_claim_valid():
    result = detect_unsupported_claims(
        "Redis caching handles authentication [app/indexer/search.py#chunk=0].",
        EVIDENCE,
    )

    assert not result.passed
    assert result.should_retry


def test_claim_check_is_skipped_without_retrieved_evidence():
    result = detect_unsupported_claims(
        "The answer is [app/indexer/search.py#chunk=0].",
        "",
    )

    assert result.passed


def test_agent_refuses_when_retry_still_contains_unsupported_claim(monkeypatch):
    agent = Agent()
    agent._allowed_citations = {"app/indexer/search.py#chunk=0"}
    agent._evidence_context = EVIDENCE
    monkeypatch.setattr(
        agent.llm,
        "chat",
        lambda messages, tools=None: {
            "choices": [{
                "message": {
                    "content": (
                        "Redis caching handles authentication "
                        "[app/indexer/search.py#chunk=0]."
                    )
                }
            }]
        },
    )

    result = agent._verify_answer(
        "Redis caching handles authentication [app/indexer/search.py#chunk=0].",
        retrieval_task=True,
    )

    assert result == _REFUSE_MESSAGE


def test_agent_accepts_supported_claim_after_retry(monkeypatch):
    agent = Agent()
    agent._allowed_citations = {"app/indexer/search.py#chunk=0"}
    agent._evidence_context = EVIDENCE
    monkeypatch.setattr(
        agent.llm,
        "chat",
        lambda messages, tools=None: {
            "choices": [{
                "message": {
                    "content": (
                        "The search function uses keyword similarity "
                        "[app/indexer/search.py#chunk=0]."
                    )
                }
            }]
        },
    )

    result = agent._verify_answer(
        "Redis caching handles authentication [app/indexer/search.py#chunk=0].",
        retrieval_task=True,
    )

    assert "keyword similarity" in result
