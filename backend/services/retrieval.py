import numpy as np
from sqlalchemy.orm import Session
from database.models import PaperChunk
from services.embeddings import encode
from core.settings import settings

def retrieve(db: Session, owner_id: str, query: str, paper_ids: list[int]) -> list[dict]:
    records = db.query(PaperChunk).filter(
        PaperChunk.owner_id == owner_id, PaperChunk.paper_id.in_(paper_ids)
    ).all()
    if not records:
        return []
    query_vector = np.asarray(encode([query])[0], dtype=np.float32)
    scored = []
    for record in records:
        vector = np.asarray(record.embedding, dtype=np.float32)
        score = float(np.dot(query_vector, vector))
        scored.append((score, record))

    # Comparative tasks keep the strongest passage from every selected paper, then fill by relevance.
    best_by_paper = {}
    for score, record in sorted(scored, key=lambda pair: pair[0], reverse=True):
        if record.paper_id not in best_by_paper:
            best_by_paper[record.paper_id] = (score, record)
    chosen = list(best_by_paper.values()) if len(paper_ids) > 1 else []
    selected_ids = {record.id for _, record in chosen}
    for score, record in sorted(scored, key=lambda pair: pair[0], reverse=True):
        if record.id not in selected_ids and len(chosen) < max(settings.RAG_TOP_K, len(paper_ids)):
            chosen.append((score, record))
    return [
        {"paper_id": record.paper_id, "page": record.page_number, "excerpt": record.text,
         "relevance": round(score, 4)}
        for score, record in sorted(chosen, key=lambda pair: pair[0], reverse=True)
    ]
