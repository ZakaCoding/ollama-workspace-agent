# Approximate token count: 1 token ≈ 4 chars for English/code text.
from app.config import context_window_tokens
from app.indexer.relevance import coverage, exact_signals


_CHARS_PER_TOKEN = 4

# Reserve budget for system prompt + tools + conversation + output.
_SYSTEM_RESERVE_TOKENS = 1500
_TOOLS_RESERVE_TOKENS = 800
_CONVERSATION_RESERVE_TOKENS = 2000
_OUTPUT_RESERVE_TOKENS = 1024


class ContextBuilder:

    def __init__(
        self,
        model_context_tokens: int | None = None,
        max_results: int = 5,
        score_threshold: float = 0.25,
        max_chunks_per_file: int = 2,
        max_chunk_chars: int = 3000,
    ):
        if model_context_tokens is None:
            model_context_tokens = context_window_tokens()
        self.model_context_tokens = model_context_tokens

        # Token-aware budget: subtract all reserved slots.
        reserved = (
            _SYSTEM_RESERVE_TOKENS
            + _TOOLS_RESERVE_TOKENS
            + _CONVERSATION_RESERVE_TOKENS
            + _OUTPUT_RESERVE_TOKENS
        ) * _CHARS_PER_TOKEN
        self.max_chars = max(
            2000,
            model_context_tokens * _CHARS_PER_TOKEN - reserved,
        )
        self.max_results = max_results
        self.score_threshold = score_threshold
        self.max_chunks_per_file = max_chunks_per_file
        self.max_chunk_chars = max_chunk_chars
        self.citations: set[str] = set()

    def tool_excerpt(self, content: str, query: str, limit: int, *, command: bool = False) -> str:
        if len(content) <= limit:
            return content
        if command:
            marker = "\n[tool output omitted]\n"
            available = max(0, limit - len(marker))
            head = available // 2
            tail = available - head
            return (content[:head] + marker + (content[-tail:] if tail else ""))[:limit]
        return self._excerpt(content, query, limit)

    def bound_tool_messages(self, messages: list[dict], query: str) -> list[dict]:
        """Share one evidence budget across tool results without breaking call IDs."""
        if not any(m.get("role") == "tool" for m in messages):
            return messages
        # Current tool observations supersede the speculative pre-edit search.
        bounded = [dict(m) for m in messages if not (
            m.get("role") == "system" and (m.get("content") or "").startswith(
                "Repository evidence for the requested change"
            )
        )]
        names = {call["id"]: call["function"]["name"]
                 for m in bounded for call in (m.get("tool_calls") or [])}
        results = [m for m in bounded if m.get("role") == "tool"]
        remaining = self.max_chars
        # Preserve small statuses intact before dividing space between long outputs.
        for index, message in enumerate(sorted(results, key=lambda m: len(m.get("content") or ""))):
            limit = min(self.max_chunk_chars, remaining // (len(results) - index))
            message["content"] = self.tool_excerpt(
                message.get("content") or "", query, limit,
                command=names.get(message.get("tool_call_id")) == "run_command",
            )
            remaining -= len(message["content"])
        return bounded

    @staticmethod
    def _excerpt(content: str, query: str, limit: int) -> str:
        """Select a contiguous source window; never generate evidence text."""
        if len(content) <= limit:
            return content
        marker = "[excerpt omitted]"
        available = limit - 2 * (len(marker) + 1)
        if available <= 0:
            return ""
        # Rank lines, retaining nearby source for definitions and qualifiers.
        best_offset = 0
        best_score = 0.0
        offset = 0
        for line in content.splitlines(keepends=True):
            signals = exact_signals(query, "", line)
            score = coverage(query, line) + signals["symbol_score"] + signals["phrase_score"]
            if score > best_score:
                best_score, best_offset = score, offset
            offset += len(line)
        start = max(0, best_offset - available // 4)
        # A match near EOF needs less context, not a full window of padding
        # before it. Keeping the match early also survives tighter later budgets.
        end = min(len(content), start + available)
        # Prefer whole lines, but retain bounded excerpts of very long lines.
        boundary = content.find("\n", start, best_offset)
        if start and boundary >= 0:
            start = boundary + 1
        boundary = content.rfind("\n", max(start, best_offset), end)
        if boundary > max(start, best_offset):
            end = boundary
        return (
            (marker + "\n" if start else "")
            + content[start:end]
            + ("\n" + marker if end < len(content) else "")
        )

    def build(self, results: list[dict], query: str = "", *, tool_output: bool = False) -> str:
        self.citations = set()
        heading = (f"Found {max(1, self.max_results)} source chunk(s).\n\n" if tool_output
                   else "REPOSITORY CONTEXT\n==================\n\n")
        separator = "\n---\n\n"
        candidates = []
        chunks_per_file: dict[str, int] = {}
        seen = set()
        for result in results:
            if len(candidates) >= self.max_results:
                break
            score = result.get("score", 0)
            path = result.get("path", "unknown")
            content = result.get("content", "")
            key = (path, content)
            if (score < self.score_threshold or not content.strip() or key in seen
                    or chunks_per_file.get(path, 0) >= self.max_chunks_per_file):
                continue
            chunk_index = result.get("chunk_index", "?")
            header = (
                f"EVIDENCE: [{path}#chunk={chunk_index}]\n"
                f"FILE: {path}\nCHUNK: {chunk_index}\n"
                f"RELEVANCE: {score:.4f}\n"
                f"CITE THIS EVIDENCE AS: [{path}#chunk={chunk_index}]\nCONTENT:\n"
            )
            if tool_output:
                header = (
                    f"EVIDENCE: [{path}#chunk={chunk_index}]\n"
                    f"FILE: {path}\nCHUNK: {chunk_index}\nCONTENT:\n"
                )
            # Skip metadata that cannot fit with a useful source excerpt.
            if len(header) + 80 > self.max_chars - len(heading):
                continue
            candidates.append((header, content, f"{path}#chunk={chunk_index}"))
            seen.add(key)
            chunks_per_file[path] = chunks_per_file.get(path, 0) + 1

        sections = []
        remaining = self.max_chars - len(heading)
        for index, (header, content, citation) in enumerate(candidates):
            slots = len(candidates) - index
            share = remaining // slots
            overhead = len(header) + 1 + (len(separator) if sections else 0)
            limit = min(self.max_chunk_chars, share - overhead)
            excerpt = self._excerpt(content, query, limit) if limit > 0 else ""
            if not excerpt:
                continue
            section = header + excerpt + "\n"
            remaining -= len(section) + (len(separator) if sections else 0)
            sections.append(section)
            self.citations.add(citation)
        if tool_output:
            heading = f"Found {len(sections)} source chunk(s).\n\n"
        return heading + separator.join(sections) if sections else ""
