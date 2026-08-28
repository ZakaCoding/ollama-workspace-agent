from typing import Any


class ContextBuilder:

    def build_search_context(
        self,
        results: list[Any],
        max_chars: int = 12000,
    ) -> str:

        if not results:
            return ""

        sections = []
        total = 0

        for result in results:

            if isinstance(result, dict):
                path = result.get("path", "unknown")
                content = result.get(
                    "content",
                    result.get("text", ""),
                )
            else:
                path = getattr(
                    result,
                    "path",
                    "unknown",
                )

                content = getattr(
                    result,
                    "content",
                    getattr(result, "text", ""),
                )

            section = (
                f"### {path}\n"
                f"{content}"
            )

            if total + len(section) > max_chars:
                remaining = max_chars - total

                if remaining <= 0:
                    break

                section = section[:remaining]

            sections.append(section)
            total += len(section)

            if total >= max_chars:
                break

        if not sections:
            return ""

        return (
            "The following repository context was "
            "retrieved from semantic search:\n\n"
            + "\n\n".join(sections)
        )
