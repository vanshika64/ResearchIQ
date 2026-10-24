from functools import lru_cache
from sentence_transformers import SentenceTransformer
from core.settings import settings

@lru_cache(maxsize=1)
def model():
    return SentenceTransformer(
        settings.EMBEDDINGS_MODEL,
        local_files_only=settings.HF_LOCAL_FILES_ONLY,
    )

def encode(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    vectors = model().encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return vectors.tolist()
