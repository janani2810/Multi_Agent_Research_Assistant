"""LangGraph Orchestration - Multi-Agent Research Workflow"""

# CRITICAL: Load environment variables FIRST!
from dotenv import load_dotenv
import os
load_dotenv()  # Load .env file before anything else!

from typing import Dict, Any
from agents.research_agent import ResearchAgent
from agents.analysis_agent import AnalysisAgent
from agents.writer_agent import WriterAgent
from agents.critic_agent import CriticAgent
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class ResearchState(BaseModel):
    """State object for research workflow"""
    topic: str
    research_data: Any = None
    analysis_data: Any = None
    draft_report: Any = None
    review_result: Any = None
    final_report: Any = None
    human_approval: bool = False
    revision_count: int = 0
    status: str = "initializing"
    error: str = None


class ResearchOrchestrator:
    """Orchestrates multi-agent research workflow"""
    
    def __init__(self):
        """Initialize orchestrator with all agents"""
        logger.info("🚀 Initializing agents...")
        
        try:
            # Verify API keys are loaded
            sarvam_key = os.getenv("SARVAM_API_KEY")
            tavily_key = os.getenv("TAVILY_API_KEY")
            
            if not sarvam_key:
                raise ValueError("SARVAM_API_KEY not found in environment variables")
            if not tavily_key:
                raise ValueError("TAVILY_API_KEY not found in environment variables")
            
            logger.info("✅ API keys loaded successfully")
            logger.info(f"   SARVAM: {sarvam_key[:20]}...")
            logger.info(f"   TAVILY: {tavily_key[:20]}...")
            
            # Initialize agents
            logger.info("Initializing research agent...")
            self.research_agent = ResearchAgent()
            logger.info("✅ Research agent initialized")
            
            logger.info("Initializing analysis agent...")
            self.analysis_agent = AnalysisAgent()
            logger.info("✅ Analysis agent initialized")
            
            logger.info("Initializing writer agent...")
            self.writer_agent = WriterAgent()
            logger.info("✅ Writer agent initialized")
            
            logger.info("Initializing critic agent...")
            self.critic_agent = CriticAgent()
            logger.info("✅ Critic agent initialized")
            
            logger.info("✅ All agents initialized successfully!")
            
        except Exception as e:
            logger.error(f"Failed to initialize agents: {e}", exc_info=True)
            raise
    
    def run_research(self, topic: str) -> Dict[str, Any]:
        """
        Execute complete research workflow
        
        Args:
            topic: Research topic
            
        Returns:
            Dictionary with research results
        """
        logger.info(f"Starting research for: {topic}")
        
        state = ResearchState(topic=topic)
        
        try:
            # Phase 1: Research
            logger.info("=" * 60)
            logger.info("PHASE 1: RESEARCH")
            logger.info("=" * 60)
            state.status = "researching"
            logger.info(f"Researching topic: {topic}")
            state.research_data = self.research_agent.research(topic)
            logger.info(f"✅ Research complete. Found {len(state.research_data.results)} result sets")
            logger.info(f"   Summary: {state.research_data.summary[:100]}...")
            
            # Phase 2: Analysis
            logger.info("=" * 60)
            logger.info("PHASE 2: ANALYSIS")
            logger.info("=" * 60)
            state.status = "analyzing"
            logger.info("Analyzing research findings...")
            state.analysis_data = self.analysis_agent.analyze(
                topic,
                state.research_data.results
            )
            logger.info(f"✅ Analysis complete")
            logger.info(f"   Key findings: {len(state.analysis_data.key_findings)}")
            logger.info(f"   Themes identified: {len(state.analysis_data.themes)}")
            
            # Phase 3: Writing
            logger.info("=" * 60)
            logger.info("PHASE 3: WRITING")
            logger.info("=" * 60)
            state.status = "writing"
            logger.info("Generating report...")
            state.draft_report = self.writer_agent.write_report(
                topic,
                state.analysis_data.key_findings,
                state.analysis_data.themes,
                state.analysis_data.analysis,
                state.research_data.results
            )
            logger.info(f"✅ Report generated")
            logger.info(f"   Title: {state.draft_report.title}")
            logger.info(f"   Sections: {', '.join(state.draft_report.sections)}")
            
            # Phase 4: Critique
            logger.info("=" * 60)
            logger.info("PHASE 4: CRITIQUE & QUALITY REVIEW")
            logger.info("=" * 60)
            state.status = "critiquing"
            logger.info("Reviewing report quality...")
            state.review_result = self.critic_agent.review(
                topic,
                state.draft_report.markdown,
                state.analysis_data.key_findings
            )
            logger.info(f"✅ Review complete")
            logger.info(f"   Quality Score: {state.review_result.overall_score}/100")
            logger.info(f"   Passed Review: {state.review_result.passed_review}")
            
            # Phase 5: Finalization
            logger.info("=" * 60)
            logger.info("PHASE 5: FINALIZATION")
            logger.info("=" * 60)
            state.status = "completed"
            state.final_report = state.draft_report
            
            logger.info("=" * 60)
            logger.info("✅ RESEARCH COMPLETE")
            logger.info("=" * 60)
            logger.info(f"Topic: {topic}")
            logger.info(f"Quality Score: {state.review_result.overall_score}/100")
            logger.info(f"Report Title: {state.final_report.title}")
            logger.info(f"Status: {state.status}")
            
        except Exception as e:
            logger.error(f"Research error: {str(e)}", exc_info=True)
            state.status = "error"
            state.error = str(e)
            raise
        
        return {
            'status': state.status,
            'topic': state.topic,
            'research_data': state.research_data,
            'analysis_data': state.analysis_data,
            'draft_report': state.draft_report,
            'review_result': state.review_result,
            'final_report': state.final_report,
            'error': state.error
        }