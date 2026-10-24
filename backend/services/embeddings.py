import os
from functools import lru_cache
from pathlib import Path

from core.settings import settings

# Keep the model cache inside the service directory so Render's build-time
# preload is available to the running service as part of the deployed image.
os.environ.setdefault("HF_HOME", str(Path(__file__).resolve().parents[1] / ".hf_cache"))

@lru_cache(maxsize=1)
def model():
    # Import PyTorch only when an upload or query actually needs embeddings.
    # This keeps the lightweight API routes available on small instances.
    from sentence_transformers import SentenceTransformer

    try:
        return SentenceTransformer(
            settings.EMBEDDINGS_MODEL,
            local_files_only=settings.HF_LOCAL_FILES_ONLY,
            device="cpu",
        )
    except Exception as exc:
        mode = "local cache" if settings.HF_LOCAL_FILES_ONLY else "Hugging Face Hub"
        raise RuntimeError(
            f"Could not load embedding model '{settings.EMBEDDINGS_MODEL}' from the {mode}. "
            "For Render, preload it during the build with `python preload_embedding_model.py` "
            "and set HF_LOCAL_FILES_ONLY=true, or allow outbound HTTPS to huggingface.co. "
            f"Underlying error: {exc}"
        ) from exc

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
