from functools import lru_cache
from core.settings import settings

@lru_cache(maxsize=1)
def model():
    # Import PyTorch only when an upload or query actually needs embeddings.
    # This keeps the lightweight API routes available on small instances.
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(
        settings.EMBEDDINGS_MODEL,
        local_files_only=settings.HF_LOCAL_FILES_ONLY,
        device="cpu",
    )

def encode(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    vectors = model().encode(
        texts,
        batch_size=8,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return vectors.tolist()
