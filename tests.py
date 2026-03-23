"""Test suite for multi-agent research system with Sarvam API"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Test configuration
@pytest.fixture
def mock_env():
    """Mock environment variables"""
    with patch.dict(os.environ, {
        'SARVAM_API_KEY': 'test-sarvam-key-12345',
        'TAVILY_API_KEY': 'test-tavily-key-67890'
    }):
        yield


class TestSarvamWrapper:
    """Test Sarvam API wrapper"""
    
    def test_sarvam_llm_initialization(self):
        """Test SarvamLLM wrapper initialization"""
        with patch.dict(os.environ, {'SARVAM_API_KEY': 'test-key'}):
            from sarvam_wrapper import SarvamLLM
            llm = SarvamLLM(model="Sarvam-2B", temperature=0.5)
            assert llm.model == "Sarvam-2B"
            assert llm.temperature == 0.5


class TestResearchAgent:
    """Test research agent functionality"""

    def test_research_agent_initialization(self, mock_env):
        """Test research agent initialization"""
        with patch('agents.research_agent.TavilyClient'):
            from agents.research_agent import ResearchAgent
            agent = ResearchAgent()
            assert agent.llm is not None
            assert agent.tavily is not None

    def test_generate_search_queries(self, mock_env):
        """Test search query generation"""
        with patch('agents.research_agent.TavilyClient'):
            with patch('agents.research_agent.SarvamLLM') as mock_llm:
                mock_instance = Mock()
                mock_response = Mock()
                mock_response.content = "Query 1\nQuery 2\nQuery 3\nQuery 4\nQuery 5"
                mock_instance.invoke.return_value = mock_response
                mock_llm.return_value = mock_instance
                
                from agents.research_agent import ResearchAgent
                agent = ResearchAgent()
                agent.llm = mock_instance
                
                queries = agent.generate_search_queries("AI in healthcare", num_queries=5)
                assert len(queries) == 5
                assert all(isinstance(q, str) for q in queries)


class TestAnalysisAgent:
    """Test analysis agent functionality"""

    def test_analysis_agent_initialization(self, mock_env):
        """Test analysis agent initialization"""
        with patch('agents.analysis_agent.SarvamLLM'):
            from agents.analysis_agent import AnalysisAgent
            agent = AnalysisAgent()
            assert agent.llm is not None


class TestWriterAgent:
    """Test writer agent functionality"""

    def test_writer_agent_initialization(self, mock_env):
        """Test writer agent initialization"""
        with patch('agents.writer_agent.SarvamLLM'):
            from agents.writer_agent import WriterAgent
            agent = WriterAgent()
            assert agent.llm is not None


class TestCriticAgent:
    """Test critic agent functionality"""

    def test_critic_agent_initialization(self, mock_env):
        """Test critic agent initialization"""
        with patch('agents.critic_agent.SarvamLLM'):
            from agents.critic_agent import CriticAgent
            agent = CriticAgent()
            assert agent.llm is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])