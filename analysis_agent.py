from typing import Any
from sarvam_wrapper import SarvamLLM
from pydantic import BaseModel
from agents.research_agent import strip_think_tags
import os
import logging

logger = logging.getLogger(__name__)


class AnalysisResult(BaseModel):
    topic: str
    key_findings: list[str]
    themes: list[str]
    data_points: dict[str, Any]
    analysis: str


class AnalysisAgent:
    """Agent responsible for synthesizing research findings"""

    def __init__(self):
        self.llm = SarvamLLM(
            model="sarvam-m",
            temperature=0.5
        )

    def extract_key_findings(self, research_results: dict) -> list[str]:
        """Extract key findings from search results"""
        all_content = []
        for query, results in research_results.items():
            for result in results:
                all_content.append(f"{result['title']}: {result['content'][:300]}")

        content_str = '\n'.join(all_content[:20])

        prompt = f"""From the following research results, extract 5-7 key findings as bullet points.
Focus on actionable, significant insights.

Results:
{content_str}

Return ONLY the key findings, one per line starting with a dash."""

        response = self.llm.invoke(prompt)
        clean = strip_think_tags(response.content)
        findings = [f.strip() for f in clean.split('\n') if f.strip().startswith('-')]

        if not findings:
            logger.warning("No findings extracted after stripping think tags.")

        return findings

    def identify_themes(self, research_results: dict) -> list[str]:
        """Identify major themes from research"""
        all_titles = []
        all_content = []

        for query, results in research_results.items():
            for result in results:
                all_titles.append(result['title'])
                all_content.append(result['content'][:200])

        combined = ' '.join(all_titles) + ' ' + ' '.join(all_content)

        prompt = f"""Identify 4-6 major recurring themes in the following research data:

{combined[:2000]}

Return ONLY the themes, one per line, no numbering."""

        response = self.llm.invoke(prompt)
        clean = strip_think_tags(response.content)
        themes = [t.strip() for t in clean.split('\n') if t.strip()]

        if not themes:
            logger.warning("No themes extracted after stripping think tags.")

        return themes[:6]

    def synthesize_analysis(self, topic: str, research_results: dict,
                            key_findings: list[str], themes: list[str]) -> str:
        """Create comprehensive synthesis analysis"""

        all_content = []
        for query, results in research_results.items():
            for result in results:
                all_content.append(f"- {result['title']}: {result['content'][:250]}")

        content_preview = '\n'.join(all_content[:15])

        prompt = f"""Create a comprehensive analysis of the following research on "{topic}":

Key Findings:
{chr(10).join('- ' + f for f in key_findings)}

Themes:
{chr(10).join('- ' + t for t in themes)}

Research Preview:
{content_preview}

Write 3-4 paragraphs analyzing:
1. Current state and trends
2. Key patterns and connections
3. Implications and significance
4. Areas needing further investigation"""

        response = self.llm.invoke(prompt)
        return strip_think_tags(response.content)

    def analyze(self, topic: str, research_results: dict) -> AnalysisResult:
        """Main analysis workflow"""
        logger.info(f"Starting analysis for topic: {topic}")

        key_findings = self.extract_key_findings(research_results)
        logger.info(f"Extracted {len(key_findings)} key findings")

        themes = self.identify_themes(research_results)
        logger.info(f"Identified {len(themes)} themes")

        analysis = self.synthesize_analysis(topic, research_results, key_findings, themes)
        logger.info("Analysis complete")

        return AnalysisResult(
            topic=topic,
            key_findings=key_findings,
            themes=themes,
            data_points={
                'total_sources': sum(len(r) for r in research_results.values()),
                'search_queries': len(research_results),
                'themes_count': len(themes)
            },
            analysis=analysis
        )
