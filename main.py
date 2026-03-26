"""FastAPI Backend Server - Multi-Agent Research System"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import logging
from datetime import datetime
from pathlib import Path
from io import BytesIO

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load env
from dotenv import load_dotenv
load_dotenv()

# Imports
from orchestration import ResearchOrchestrator
from utils import markdown_to_pdf, format_research_for_display

# App
app = FastAPI(title="Multi-Agent Research Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# State
research_sessions = {}
orchestrator = None

OUTPUT_DIR = Path("reports")
OUTPUT_DIR.mkdir(exist_ok=True)


# Models
class ResearchRequest(BaseModel):
    topic: str
    auto_approve: bool = False


class ApprovalRequest(BaseModel):
    session_id: str
    approved: bool


# Startup
@app.on_event("startup")
async def startup():
    global orchestrator
    logger.info("🚀 Initializing orchestrator...")
    orchestrator = ResearchOrchestrator()
    logger.info("✅ Orchestrator ready")


# Health check
@app.get("/health")
async def health():
    return {"status": "ok"}


# Root
@app.get("/")
async def root():
    return {"status": "running"}


# ── Start Research ─────────────────────────────────────────────────────────────
@app.post("/research/start")
async def start_research(request: ResearchRequest, background_tasks: BackgroundTasks):
    session_id = f"research_{int(datetime.now().timestamp())}"

    research_sessions[session_id] = {
        "topic": request.topic,
        "status": "Starting",
        "progress": 0,
        "error": None,
        "research_data": None,
        "analysis_data": None,
        "draft_report": None,
        "review_result": None,
        "final_report": None,
    }

    background_tasks.add_task(
        run_research_workflow,
        session_id,
        request.topic,
        request.auto_approve
    )

    return {"session_id": session_id}


# ── Status ─────────────────────────────────────────────────────────────────────
@app.get("/research/status/{session_id}")
async def get_status(session_id: str):
    if session_id not in research_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    s = research_sessions[session_id]
    return {
        "status":   s["status"],
        "progress": s["progress"],
        "topic":    s["topic"],
        "error":    s["error"],
    }


# ── Report (markdown + metadata) ───────────────────────────────────────────────
@app.get("/research/report/{session_id}")
async def get_report(session_id: str):
    if session_id not in research_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    s = research_sessions[session_id]

    if s["status"] != "Completed" or not s.get("final_report"):
        raise HTTPException(status_code=400, detail="Report not ready yet")

    review = s.get("review_result")
    quality_score = None
    if review:
        quality_score = getattr(review, "overall_score", None)
        if quality_score is None and isinstance(review, dict):
            quality_score = review.get("overall_score")

    return {
        "markdown":      s["final_report"].markdown,
        "title":         s["final_report"].title,
        "sections":      s["final_report"].sections,
        "quality_score": quality_score,
    }


# ── PDF Download ───────────────────────────────────────────────────────────────
@app.get("/research/download/{session_id}")
async def download_pdf(session_id: str):
    if session_id not in research_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    s = research_sessions[session_id]

    if s["status"] != "Completed" or not s.get("final_report"):
        raise HTTPException(status_code=400, detail="Report not ready yet")

    try:
        pdf_buffer: BytesIO = markdown_to_pdf(
            s["final_report"].markdown,
            s["final_report"].title
        )

        filename = f"research_{session_id}.pdf"

        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        logger.error(f"PDF generation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")


# ── Background Workflow ────────────────────────────────────────────────────────
async def run_research_workflow(session_id: str, topic: str, auto_approve: bool):
    s = research_sessions[session_id]

    try:
        # Phase 1: Research
        logger.info("🔍 Research phase")
        s["status"] = "Research"
        s["progress"] = 10
        s["research_data"] = orchestrator.research_agent.research(topic)
        s["progress"] = 25

        # Phase 2: Analysis
        logger.info("📊 Analysis phase")
        s["status"] = "Analysis"
        s["progress"] = 35
        s["analysis_data"] = orchestrator.analysis_agent.analyze(
            topic,
            s["research_data"].results
        )
        s["progress"] = 50

        # Phase 3: Writing
        logger.info("✍️ Writing phase")
        s["status"] = "Writing"
        s["progress"] = 60
        s["draft_report"] = orchestrator.writer_agent.write_report(
            topic,
            s["analysis_data"].key_findings,
            s["analysis_data"].themes,
            s["analysis_data"].analysis,
            s["research_data"].results
        )
        s["progress"] = 75

        # Phase 4: Critic
        logger.info("⭐ Critic phase")
        s["status"] = "Review"
        s["progress"] = 85
        s["review_result"] = orchestrator.critic_agent.review(
            topic,
            s["draft_report"].markdown,
            s["analysis_data"].key_findings
        )
        s["progress"] = 90

        # Finalize
        logger.info("✅ Completed")
        s["final_report"] = s["draft_report"]
        s["status"] = "Completed"
        s["progress"] = 100

    except Exception as e:
        logger.error(f"Workflow error: {e}", exc_info=True)
        s["status"] = "Error"
        s["error"] = str(e)
        s["progress"] = 0
