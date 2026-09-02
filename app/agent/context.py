class ContextBuilder:

    def __init__(
        self,
        max_chars: int = 12000,
        max_results: int = 5,
        score_threshold: float = 0.25,
        max_chunks_per_file: int = 2,
        max_chunk_chars: int = 3000,
    ):
        self.max_chars = max_chars
        self.max_results = max_results
        self.score_threshold = score_threshold
        self.max_chunks_per_file = max_chunks_per_file
        self.max_chunk_chars = max_chunk_chars

    def build(self, results: list[dict]) -> str:
        if not results:
            return ""

        sections = []
        used_chars = 0
        chunks_per_file: dict[str, int] = {}

        for result in results:
            if used_chars >= self.max_chars:
                break

            if len(sections) >= self.max_results:
                break

            score = result.get("score", 0)
            if score < self.score_threshold:
                continue

            path = result.get("path", "unknown")
            if chunks_per_file.get(path, 0) >= self.max_chunks_per_file:
                continue

            chunk_index = result.get("chunk_index", "?")
            content = result.get("content", "")

            if len(content) > self.max_chunk_chars:
                content = content[: self.max_chunk_chars]

            section = (
                f"FILE: {path}\n"
                f"CHUNK: {chunk_index}\n"
                f"RELEVANCE: {score:.4f}\n"
                f"CONTENT:\n{content}\n"
            )

            remaining = self.max_chars - used_chars
            if len(section) > remaining:
                section = section[:remaining]

            sections.append(section)
            used_chars += len(section)
            chunks_per_file[path] = chunks_per_file.get(path, 0) + 1

        if not sections:
            return ""

        return (
            "REPOSITORY CONTEXT\n"
            "==================\n\n"
            + "\n---\n\n".join(sections)
        )
