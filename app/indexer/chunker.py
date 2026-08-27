def chunk_text(
    text: str,
    chunk_size: int = 12000,
    overlap: int = 1000,
) -> list[str]:

    if not text:
        return []

    if overlap >= chunk_size:
        raise ValueError(
            "overlap must be smaller than chunk_size"
        )

    chunks = []

    start = 0

    while start < len(text):
        end = start + chunk_size

        chunks.append(
            text[start:end]
        )

        if end >= len(text):
            break

        start = end - overlap

    return chunks
