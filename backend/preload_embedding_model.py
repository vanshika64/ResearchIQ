"""Download and warm the configured embedding model during a Render build."""

import os
from pathlib import Path
import time

from core.settings import settings

os.environ.setdefault("HF_HOME", str(Path(__file__).resolve().parent / ".hf_cache"))

from sentence_transformers import SentenceTransformer


def main() -> None:
    last_error = None
    for attempt in range(1, 4):
        try:
            model = SentenceTransformer(
                settings.EMBEDDINGS_MODEL,
                local_files_only=False,
                device="cpu",
            )
            model.encode(["ResearchIQ embedding model warmup"], show_progress_bar=False)
            print(f"Embedding model ready: {settings.EMBEDDINGS_MODEL}")
            return
        except Exception as exc:
            last_error = exc
            print(f"Model download attempt {attempt}/3 failed: {exc}")
            if attempt < 3:
                time.sleep(attempt * 5)

    raise RuntimeError(
        f"Could not preload {settings.EMBEDDINGS_MODEL}. Check outbound HTTPS access to "
        "huggingface.co and retry the Render deploy."
    ) from last_error


if __name__ == "__main__":
    main()
