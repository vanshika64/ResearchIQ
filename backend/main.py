from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
from fastapi.responses import JSONResponse
from database.models import Base, engine
from database.migrations import migrate_schema
from api import routes
from core.settings import settings
from utils.logger import get_logger

Base.metadata.create_all(bind=engine)
migrate_schema(engine)
app = FastAPI(title="ResearchIQ", description="Evidence-grounded medical literature assistant", version="1.0.0")
origins = [x.strip() for x in settings.CORS_ORIGINS.split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins if origins != ["*"] else ["*"], allow_credentials=origins != ["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(routes.router, prefix="/api")
logger = get_logger(__name__)

@app.exception_handler(Exception)
async def log_unhandled_error(request: Request, exc: Exception):
    logger.exception("Unhandled server error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={
        "detail": "Unexpected backend error. Check backend/logs/researchiq.log for the traceback."
    })

@app.get("/health")
def health(): return {"status": "ok", "service": "ResearchIQ"}
