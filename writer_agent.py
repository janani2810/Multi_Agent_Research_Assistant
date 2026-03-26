from typing import Any
from sarvam_wrapper import SarvamLLM
from pydantic import BaseModel
from agents.research_agent import strip_think_tags
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)


class WriterResult(BaseModel):
    markdown: str
    title: str
    sections: list[str]


class WriterAgent:
    """Agent responsible for writing structured reports"""

    def __init__(self):
        self.llm = SarvamLLM(
            model="sarvam-m",
            temperature=0.7
        )

    def create_executive_summary(self, topic: str, key_findings: list[str]) -> str:
        """Create executive summary section"""
        findings_text = '\n'.join(f'- {f}' for f in key_findings)

        prompt = f"""Write a compelling 2-3 paragraph executive summary for a research report on "{topic}".

Key Findings:
{findings_text}

Make it professional, concise, and suitable for decision-makers."""

        response = self.llm.invoke(prompt)
        return strip_think_tags(response.content)

    def create_detailed_findings(self, key_findings: list[str]) -> str:
        """Expand key findings into detailed section"""
        findings_text = '\n'.join(f'{i+1}. {f}' for i, f in enumerate(key_findings))

        prompt = f"""For each of these key findings, provide 1-2 sentences of additional context and detail:

{findings_text}

Format as a numbered list with expanded explanations."""

        response = self.llm.invoke(prompt)
        return strip_think_tags(response.content)

    def create_methodology(self, research_data: dict) -> str:
        """Create methodology section"""
        query_count = len(research_data)
        total_sources = sum(len(r) for r in research_data.values())

        prompt = f"""Write a brief methodology section (3-4 sentences) for a research report that:
- Conducted {query_count} targeted web searches
- Gathered {total_sources} unique sources
- Used AI-powered synthesis for analysis

Focus on transparency and rigor."""

        response = self.llm.invoke(prompt)
        return strip_think_tags(response.content)

    def create_recommendations(self, key_findings: list[str], analysis: str) -> str:
        """Generate recommendations based on findings"""
        findings_text = '\n'.join(f'- {f}' for f in key_findings)

        prompt = f"""Based on the following research findings and analysis, provide 4-6 actionable recommendations:

Findings:
{findings_text}

Analysis Summary:
{analysis[:500]}

Format as numbered recommendations with brief explanations."""

        response = self.llm.invoke(prompt)
        return strip_think_tags(response.content)

    def write_report(self, topic: str, key_findings: list[str],
                     themes: list[str], analysis: str, research_data: dict) -> WriterResult:
        """Generate complete markdown report"""
        logger.info(f"Starting report writing for topic: {topic}")

        executive_summary = self.create_executive_summary(topic, key_findings)
        detailed_findings = self.create_detailed_findings(key_findings)
        methodology = self.create_methodology(research_data)
        recommendations = self.create_recommendations(key_findings, analysis)

        markdown = f"""# Research Report: {topic}

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Executive Summary

{executive_summary}

## Key Themes

{chr(10).join(f'- {theme}' for theme in themes)}

## Detailed Findings

{detailed_findings}

## Analysis

{analysis}

## Methodology

{methodology}

## Recommendations

{recommendations}

---

*This report was generated using AI-powered multi-agent research system with web search capabilities.*
"""

        sections = [
            "Executive Summary",
            "Key Themes",
            "Detailed Findings",
            "Analysis",
            "Methodology",
            "Recommendations"
        ]

        logger.info("Report writing complete")

        return WriterResult(
            markdown=markdown,
            title=f"Research Report: {topic}",
            sections=sections
        )
