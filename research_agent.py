"""Research Agent - Web Search and Information Gathering"""
 
from typing import Any
from tavily import TavilyClient
from sarvam_wrapper import SarvamLLM
from pydantic import BaseModel
import os
import logging
 
logger = logging.getLogger(__name__)
 
 
class ResearchQuery(BaseModel):
    topic: str
    query_count: int = 5
 
 
class ResearchResult(BaseModel):
    topic: str
    queries: list[str]
    results: dict[str, list[dict[str, Any]]]
    summary: str
 
 
class ResearchAgent:
    """Agent responsible for web research"""
 
    def __init__(self):
        self.tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
        self.llm = SarvamLLM(
            model="sarvam-m",
            temperature=0.3
        )
 
    def generate_search_queries(self, topic: str, num_queries: int = 5) -> list[str]:
        """Generate diverse search queries from the research topic"""
        prompt = f"""Generate {num_queries} diverse search queries to comprehensively research the topic: "{topic}"
        
Make queries specific and varied (e.g., definitions, latest developments, pros/cons, use cases, etc).
Return ONLY the queries, one per line, no numbering or extra text."""
 
        response = self.llm.invoke(prompt)
        queries = [q.strip() for q in response.content.split('\n') if q.strip()]
        return queries[:num_queries]
 
    def search(self, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        """Execute a single search query using Tavily"""
        try:
            response = self.tavily.search(query=query, max_results=max_results)
            results = []
            for result in response.get('results', []):
                results.append({
                    'title': result.get('title', ''),
                    'url': result.get('url', ''),
                    'content': result.get('content', ''),
                    'score': result.get('score', 0)
                })
            logger.info(f"Found {len(results)} results for query: {query}")
            return results
        except Exception as e:
            logger.error(f"Search error for query '{query}': {str(e)}")
            return []
 
    def research(self, topic: str) -> ResearchResult:
        """Main research workflow"""
        logger.info(f"Starting research for topic: {topic}")
 
        # Generate search queries
        queries = self.generate_search_queries(topic, num_queries=5)
        logger.info(f"Generated queries: {queries}")
 
        # Execute searches
        all_results = {}
        for query in queries:
            results = self.search(query)
            all_results[query] = results
 
        # Generate research summary
        summary_prompt = f"""Based on the following research results for topic "{topic}", provide a concise 2-3 sentence summary of the main findings:
 
Topic: {topic}
Number of unique results found: {sum(len(r) for r in all_results.values())}
 
Key sources covered: {', '.join(queries[:3])}
 
Provide a brief overview of what was discovered."""
 
        summary_response = self.llm.invoke(summary_prompt)
        summary = summary_response.content
 
        return ResearchResult(
            topic=topic,
            queries=queries,
            results=all_results,
            summary=summary
        )
 
