"""FastAPI Backend Server - Multi-Agent Research System"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, File, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import logging
from datetime import datetime
import asyncio
from pathlib import Path
from io import BytesIO

from orchestration import ResearchOrchestrator, ResearchState
from utils import markdown_to_pdf, save_markdown_file, format_research_for_display

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Multi-Agent Research Assistant",
    description="AI-powered research system with autonomous agents",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# State management
research_sessions: dict[str, ResearchState] = {}
orchestrator = ResearchOrchestrator()

# Create output directory
OUTPUT_DIR = Path("reports")
OUTPUT_DIR.mkdir(exist_ok=True)


class ResearchRequest(BaseModel):
    topic: str
    auto_approve: bool = False


class ApprovalRequest(BaseModel):
    session_id: str
    approved: bool


class ResearchResponse(BaseModel):
    session_id: str
    topic: str
    status: str
    research_complete: bool
    analysis_complete: bool
    draft_ready: bool
    review_score: int | None
    final_ready: bool
    error: str | None


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/research/start")
async def start_research(request: ResearchRequest, background_tasks: BackgroundTasks):
    """Start a new research task"""
    try:
        # Generate session ID
        session_id = f"research_{int(datetime.now().timestamp())}"
        
        logger.info(f"📋 Starting research session: {session_id} for topic: {request.topic}")
        
        # Run research in background
        if request.auto_approve:
            background_tasks.add_task(
                run_research_workflow,
                session_id,
                request.topic,
                auto_approve=True
            )
        else:
            background_tasks.add_task(
                run_research_workflow,
                session_id,
                request.topic,
                auto_approve=False
            )
        
        return {
            "session_id": session_id,
            "topic": request.topic,
            "status": "Research started",
            "message": "Research workflow has been initiated"
        }
    
    except Exception as e:
        logger.error(f"Error starting research: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/research/status/{session_id}")
async def get_research_status(session_id: str) -> ResearchResponse:
    """Get status of research session"""
    try:
        if session_id not in research_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        state = research_sessions[session_id]
        return ResearchResponse(**format_research_for_display(state, session_id))
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/research/draft/{session_id}")
async def get_draft_report(session_id: str):
    """Get draft report markdown"""
    try:
        if session_id not in research_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        state = research_sessions[session_id]
        if not state.get('draft_report'):
            raise HTTPException(status_code=400, detail="Draft report not ready")
        
        return {
            "markdown": state['draft_report'].markdown,
            "title": state['draft_report'].title,
            "sections": state['draft_report'].sections
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting draft: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/research/approve/{session_id}")
async def approve_draft(session_id: str, request: ApprovalRequest):
    """Approve draft report to proceed to critique"""
    try:
        if session_id not in research_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        state = research_sessions[session_id]
        
        if request.approved:
            logger.info(f"✅ Draft approved for session: {session_id}")
            state['human_approval'] = True
            state['status'] = "Draft approved - proceeding to critique"
            
            # Continue workflow
            continue_workflow(session_id)
        else:
            logger.info(f"❌ Draft rejected for session: {session_id}")
            state['status'] = "Draft rejected by user"
            state['error'] = "User rejected the draft report"
        
        return {"status": "Approval recorded", "approved": request.approved}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving draft: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/research/report/{session_id}")
async def get_final_report(session_id: str):
    """Get final report as JSON"""
    try:
        if session_id not in research_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        state = research_sessions[session_id]
        if not state.get('final_report'):
            raise HTTPException(status_code=400, detail="Final report not ready")
        
        return {
            "markdown": state['final_report'].markdown,
            "title": state['final_report'].title,
            "sections": state['final_report'].sections,
            "review_score": state.get('review_result', {}).get('overall_score')
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting report: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/research/download/{session_id}")
async def download_report_pdf(session_id: str):
    """Download final report as PDF"""
    try:
        if session_id not in research_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        state = research_sessions[session_id]
        if not state.get('final_report'):
            raise HTTPException(status_code=400, detail="Final report not ready")
        
        # Generate PDF
        pdf_buffer = markdown_to_pdf(
            state['final_report'].markdown,
            state['final_report'].title
        )
        
        filename = f"{session_id}_report.pdf"
        
        return FileResponse(
            pdf_buffer,
            media_type="application/pdf",
            filename=filename
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading report: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/research/sessions")
async def list_sessions():
    """List all research sessions"""
    sessions = []
    for session_id, state in research_sessions.items():
        sessions.append({
            "session_id": session_id,
            "topic": state['topic'],
            "status": state['status'],
            "final_ready": state.get('final_report') is not None
        })
    
    return {"sessions": sessions}


# Background tasks
async def run_research_workflow(session_id: str, topic: str, auto_approve: bool = False):
    """Execute research workflow"""
    try:
        logger.info(f"🚀 Executing research workflow: {session_id}")
        
        # Run research
        initial_state: ResearchState = {
            'topic': topic,
            'research_data': None,
            'analysis_data': None,
            'draft_report': None,
            'review_result': None,
            'final_report': None,
            'human_approval': auto_approve,
            'revision_count': 0,
            'status': 'Starting research...',
            'error': None
        }
        
        research_sessions[session_id] = initial_state
        
        # Phase 1: Research
        logger.info("🔍 Phase 1: Research")
        initial_state['status'] = "Researching..."
        research_data = orchestrator.research_agent.research(topic)
        initial_state['research_data'] = research_data
        
        # Phase 2: Analysis
        logger.info("📊 Phase 2: Analysis")
        initial_state['status'] = "Analyzing..."
        analysis_data = orchestrator.analysis_agent.analyze(
            topic,
            {q: r for q, r in zip(
                research_data.queries,
                [research_data.results.get(q, []) for q in research_data.queries]
            )}
        )
        initial_state['analysis_data'] = analysis_data
        
        # Phase 3: Writing
        logger.info("✍️ Phase 3: Writing")
        initial_state['status'] = "Writing draft report..."
        draft_report = orchestrator.writer_agent.write_report(
            topic,
            analysis_data.key_findings,
            analysis_data.themes,
            analysis_data.analysis,
            research_data.results
        )
        initial_state['draft_report'] = draft_report
        
        # Phase 4: Human Review
        if not auto_approve:
            logger.info("⏸️ Phase 4: Awaiting human approval")
            initial_state['status'] = "Draft ready - awaiting your approval"
            initial_state['human_approval'] = False
            
            # Wait for approval (max 30 minutes)
            for _ in range(180):  # 30 minutes with 10-second intervals
                await asyncio.sleep(10)
                if initial_state.get('human_approval'):
                    break
            
            if not initial_state.get('human_approval'):
                initial_state['status'] = "Approval timeout - auto-approving"
                initial_state['human_approval'] = True
        else:
            initial_state['status'] = "Auto-approved - proceeding to critique"
        
        # Phase 5: Critique
        logger.info("🔍 Phase 5: Critique")
        initial_state['status'] = "Critiquing report..."
        review_result = orchestrator.critic_agent.review(
            topic,
            draft_report.markdown,
            analysis_data.key_findings
        )
        initial_state['review_result'] = review_result
        
        # Phase 6: Finalization
        logger.info("✅ Phase 6: Finalization")
        initial_state['final_report'] = draft_report
        initial_state['status'] = "Report complete - ready for download"
        
        logger.info(f"✨ Research workflow complete: {session_id}")
        
    except Exception as e:
        logger.error(f"❌ Workflow error for {session_id}: {str(e)}")
        if session_id in research_sessions:
            research_sessions[session_id]['status'] = "Error"
            research_sessions[session_id]['error'] = str(e)


def continue_workflow(session_id: str):
    """Continue workflow after human approval"""
    # The background task will check human_approval flag
    pass


# ==================== SARVAM AI VOICE ENDPOINTS ====================

@app.get("/voice/available")
async def check_voice_availability():
    """Check if Sarvam AI voice features are available"""
    available = is_sarvam_available()
    return {
        "voice_features_available": available,
        "services": {
            "speech_to_text": available,
            "text_to_speech": available,
            "translation": available,
            "language_detection": available
        }
    }


@app.post("/voice/research/transcribe")
async def transcribe_research_request(
    file: UploadFile = File(...),
    language: str = "en"
):
    """
    Transcribe voice research request to text
    
    Args:
        file: Audio file (WAV, MP3, etc.)
        language: Language code (en, hi, ta, te, etc.)
    
    Returns:
        Transcribed text and detected language
    """
    if not is_sarvam_available():
        raise HTTPException(
            status_code=503,
            detail="Sarvam AI voice features not available. Configure SARVAM_API_KEY."
        )
    
    try:
        # Read audio file
        contents = await file.read()
        audio_buffer = BytesIO(contents)
        
        # Process voice research request
        sarvam_client = get_sarvam_client()
        topic, detected_lang = sarvam_client.speech_to_text(audio_buffer, language)
        
        if not topic:
            raise HTTPException(status_code=400, detail="Failed to transcribe audio")
        
        return {
            "success": True,
            "transcribed_topic": topic,
            "detected_language": detected_lang,
            "file_name": file.filename
        }
    
    except Exception as e:
        logger.error(f"Voice transcription error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/voice/research/start")
async def start_voice_research(
    file: UploadFile = File(...),
    language: str = "en",
    auto_approve: bool = False,
    background_tasks: BackgroundTasks = None
):
    """
    Start research from voice input
    
    Args:
        file: Audio file containing research topic
        language: Language of audio input
        auto_approve: Whether to auto-approve the draft
        background_tasks: FastAPI background tasks
    
    Returns:
        Session ID for tracking the research
    """
    if not is_sarvam_available():
        raise HTTPException(
            status_code=503,
            detail="Sarvam AI voice features not available. Configure SARVAM_API_KEY."
        )
    
    try:
        # Transcribe audio to get topic
        contents = await file.read()
        audio_buffer = BytesIO(contents)
        
        sarvam_client = get_sarvam_client()
        topic, detected_lang = sarvam_client.speech_to_text(audio_buffer, language)
        
        if not topic:
            raise HTTPException(status_code=400, detail="Failed to transcribe audio")
        
        # Start research with transcribed topic
        session_id = f"voice_research_{uuid.uuid4().hex[:12]}"
        
        if background_tasks:
            background_tasks.add_task(
                run_research_workflow,
                session_id,
                topic,
                auto_approve
            )
        
        return {
            "success": True,
            "session_id": session_id,
            "transcribed_topic": topic,
            "detected_language": detected_lang,
            "status": "Research started"
        }
    
    except Exception as e:
        logger.error(f"Voice research start error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/voice/summarize/{session_id}")
async def generate_voice_summary(
    session_id: str,
    target_language: str = "en",
    voice_type: str = "neural"
):
    """
    Generate audio summary of research report
    
    Args:
        session_id: Research session ID
        target_language: Language for audio output
        voice_type: Voice type (neural, standard, etc.)
    
    Returns:
        Audio file stream
    """
    if not is_sarvam_available():
        raise HTTPException(
            status_code=503,
            detail="Sarvam AI voice features not available. Configure SARVAM_API_KEY."
        )
    
    if session_id not in research_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = research_sessions[session_id]
    
    if not session.get('final_report'):
        raise HTTPException(status_code=400, detail="Report not ready yet")
    
    try:
        # Generate voice summary
        voice_agent = VoiceResearchAgent(get_sarvam_client())
        markdown_report = session['final_report'].markdown
        
        audio_data = voice_agent.generate_voice_summary(
            markdown_report,
            target_language=target_language,
            voice_type=voice_type
        )
        
        if not audio_data:
            raise HTTPException(status_code=500, detail="Failed to generate audio")
        
        # Return audio file
        audio_data.seek(0)
        return StreamingResponse(
            audio_data,
            media_type="audio/wav",
            headers={"Content-Disposition": f"attachment; filename=summary_{session_id}.wav"}
        )
    
    except Exception as e:
        logger.error(f"Voice summary generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/voice/translate")
async def translate_text(text: str, target_language: str = "en"):
    """
    Translate text using Sarvam AI
    
    Args:
        text: Text to translate
        target_language: Target language code
    
    Returns:
        Translated text
    """
    if not is_sarvam_available():
        raise HTTPException(
            status_code=503,
            detail="Sarvam AI not available. Configure SARVAM_API_KEY."
        )
    
    try:
        sarvam_client = get_sarvam_client()
        translated = sarvam_client.translate_text(text, target_language)
        
        if not translated:
            raise HTTPException(status_code=500, detail="Translation failed")
        
        return {
            "original": text,
            "translated": translated,
            "target_language": target_language
        }
    
    except Exception as e:
        logger.error(f"Translation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/voice/languages")
async def get_supported_languages():
    """Get list of supported languages"""
    if not is_sarvam_available():
        raise HTTPException(
            status_code=503,
            detail="Sarvam AI not available. Configure SARVAM_API_KEY."
        )
    
    try:
        sarvam_client = get_sarvam_client()
        languages = sarvam_client.get_supported_languages()
        
        return {
            "success": True,
            "languages": languages or {
                "speech_to_text": ["en", "hi", "ta", "te", "ma", "gu", "kn", "ml"],
                "text_to_speech": ["en", "hi", "ta", "te", "ma", "gu", "kn", "ml"],
                "translation": ["en", "hi", "ta", "te", "ma", "gu", "kn", "ml"]
            }
        }
    
    except Exception as e:
        logger.error(f"Error getting languages: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)