from pathlib import Path
import re

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import desc
from sqlalchemy.orm import Session

from api.auth import current_user
from core.settings import settings
from database.models import Paper, PaperChunk, Interaction
from database.session import get_db
from models.schemas import ResearchRequest
from utils.logger import get_logger
from services.generation import generate
from services.ingestion import extract_pages, make_chunks, embed_chunks
from services.retrieval import retrieve
from services.domain_scope import is_medical_research_paper, is_medical_research_query, is_research_gap_request

router = APIRouter()
logger = get_logger(__name__)
MAX_PDF_BYTES = 30 * 1024 * 1024

@router.get("/config")
def public_config():
    return {"supabaseUrl": settings.SUPABASE_URL, "supabaseAnonKey": settings.SUPABASE_ANON_KEY,
            "frontendUrl": settings.FRONTEND_URL}

@router.get("/health")
def api_health():
    return {"status": "ok", "llm_provider": "groq", "embeddings_provider": "huggingface"}

@router.get("/papers")
def list_papers(user=Depends(current_user), db: Session = Depends(get_db)):
    return [{"id": p.id, "title": p.title, "filename": p.filename, "created_at": p.created_at}
            for p in db.query(Paper).filter_by(owner_id=user).order_by(desc(Paper.created_at)).all()]

@router.post("/papers")
async def upload_paper(file: UploadFile = File(...), user=Depends(current_user), db: Session = Depends(get_db)):
    filename = Path(file.filename or "paper.pdf").name
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(415, "Upload a PDF file.")
    data = await file.read(MAX_PDF_BYTES + 1)
    if len(data) > MAX_PDF_BYTES:
        raise HTTPException(413, "PDF must be smaller than 30 MB.")
    try:
        pages = extract_pages(data)
        full_text = "\n\n".join(text for _, text in pages)
        title = re.sub(r"\.pdf$", "", filename, flags=re.I)
        if not is_medical_research_paper(title, full_text):
            raise HTTPException(
                422,
                "This workspace accepts medical, biomedical, disease, and healthcare research papers only. "
                "The PDF must contain medical subject matter and research content such as methods, results, or an abstract.",
            )
        chunks = make_chunks(pages)
        indexed = embed_chunks(chunks)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        logger.exception("Embedding setup failed while indexing uploaded paper")
        raise HTTPException(503, f"Embedding setup failed: {exc}") from exc
    paper = Paper(owner_id=user, title=title, filename=filename, text=full_text)
    db.add(paper)
    db.flush()
    db.add_all([PaperChunk(owner_id=user, paper_id=paper.id, position=i, page_number=item["page_number"],
                           text=item["text"], embedding=item["embedding"])
                for i, item in enumerate(indexed)])
    db.commit()
    db.refresh(paper)
    logger.info("Indexed paper_id=%s pages=%s chunks=%s", paper.id, len(pages), len(indexed))
    return {"id": paper.id, "title": paper.title, "filename": paper.filename,
            "pages": len(pages), "chunks_indexed": len(indexed), "characters": len(full_text)}

@router.delete("/papers/{paper_id}")
def delete_paper(paper_id: int, user=Depends(current_user), db: Session = Depends(get_db)):
    paper = db.query(Paper).filter_by(id=paper_id, owner_id=user).first()
    if paper is None:
        raise HTTPException(404, "Paper not found.")
    db.query(PaperChunk).filter_by(paper_id=paper.id, owner_id=user).delete()
    db.delete(paper)
    db.commit()
    return {"deleted": True}

def selected_papers(payload: ResearchRequest, owner: str, db: Session):
    query = db.query(Paper).filter(Paper.owner_id == owner)
    if payload.paper_ids:
        query = query.filter(Paper.id.in_(set(payload.paper_ids)))
    papers = query.all()
    if payload.paper_ids and len(papers) != len(set(payload.paper_ids)):
        raise HTTPException(404, "One or more selected papers were not found in your library.")
    if not papers:
        raise HTTPException(400, "Upload and select at least one paper first.")
    nonmedical = [paper.title for paper in papers if not is_medical_research_paper(paper.title, paper.text or "")]
    if nonmedical:
        raise HTTPException(
            422,
            "This workspace analyzes medical and biomedical research only. Remove or replace out-of-scope paper(s): "
            + ", ".join(nonmedical[:3]),
        )
    return papers

def source_metadata(rows, papers):
    by_id = {paper.id: paper for paper in papers}
    return [{**row, "title": by_id[row["paper_id"]].title,
             "filename": by_id[row["paper_id"]].filename} for row in rows]

@router.post("/research")
def research(payload: ResearchRequest, user=Depends(current_user), db: Session = Depends(get_db)):
    question = payload.query.strip()
    if not question:
        raise HTTPException(422, "Enter a research question or focus.")
    if is_research_gap_request(question):
        raise HTTPException(
            422,
            "Research-gap analysis is unavailable. You can ask for limitations explicitly reported in the selected papers.",
        )
    if not is_medical_research_query(question):
        raise HTTPException(
            422,
            "ResearchIQ supports medical, biomedical, disease, and healthcare research questions only. "
            "Ask about a health topic or an aspect of your selected research paper.",
        )
    papers = selected_papers(payload, user, db)
    try:
        rows = retrieve(db, user, question, [paper.id for paper in papers])
    except Exception as exc:
        raise HTTPException(503, f"Hugging Face retrieval failed: {exc}") from exc
    sources = source_metadata(rows, papers)
    if not sources:
        answer = "No indexed evidence was found in the selected papers. Try another question or re-upload the paper to build its index."
    else:
        try:
            answer = generate(payload.kind, question, sources)
        except Exception as exc:
            raise HTTPException(502, f"Groq generation failed: {exc}") from exc
    interaction = Interaction(owner_id=user, kind=payload.kind, query=question, answer=answer, sources=sources)
    db.add(interaction)
    db.commit()
    db.refresh(interaction)
    logger.info("Completed research interaction_id=%s kind=%s sources=%s", interaction.id, payload.kind, len(sources))
    return {"id": interaction.id, "kind": interaction.kind, "query": question, "answer": answer,
            "sources": sources, "created_at": interaction.created_at}

@router.post("/search")
def semantic_search(payload: ResearchRequest, user=Depends(current_user), db: Session = Depends(get_db)):
    query = payload.query.strip()
    if not query:
        raise HTTPException(422, "Enter a medical research topic to search for.")
    if not is_medical_research_query(query):
        raise HTTPException(
            422,
            "ResearchIQ searches medical, biomedical, disease, and healthcare research only. "
            "Enter a health topic or a concept from your selected paper.",
        )
    papers = selected_papers(payload, user, db)
    try:
        sources = source_metadata(retrieve(db, user, query, [paper.id for paper in papers]), papers)
    except Exception as exc:
        raise HTTPException(503, f"Hugging Face semantic search failed: {exc}") from exc
    item = Interaction(owner_id=user, kind="search", query=query,
                       answer=f"Semantic search found {len(sources)} relevant passages.", sources=sources)
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": item.id, "kind": item.kind, "query": query, "answer": item.answer,
            "sources": sources, "created_at": item.created_at}

@router.get("/history")
def history(user=Depends(current_user), db: Session = Depends(get_db)):
    return [{"id": item.id, "kind": item.kind, "query": item.query, "answer": item.answer,
             "sources": item.sources or [], "created_at": item.created_at}
            for item in db.query(Interaction).filter_by(owner_id=user).order_by(desc(Interaction.created_at)).limit(200).all()]

@router.delete("/history")
def clear_history(user=Depends(current_user), db: Session = Depends(get_db)):
    db.query(Interaction).filter_by(owner_id=user).delete()
    db.commit()
    return {"cleared": True}
