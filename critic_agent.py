from typing import Any
from sarvam_wrapper import SarvamLLM
from pydantic import BaseModel
from agents.research_agent import strip_think_tags
import os
import logging

logger = logging.getLogger(__name__)


class CriticReview(BaseModel):
    passed_review: bool
    issues: list[str]
    feedback: str
    improvement_areas: list[str]
    overall_score: int  # 0-100


class CriticAgent:
    """Agent responsible for quality review and critique"""

    def __init__(self):
        self.llm = SarvamLLM(
            model="sarvam-m",
            temperature=0.5
        )

    def check_completeness(self, markdown: str, topic: str) -> dict[str, Any]:
        """Check if report covers the topic comprehensively"""
        prompt = f"""Review this research report for completeness on topic "{topic}":

{markdown[:2000]}

Check for:
1. All major aspects of the topic covered?
2. Clear structure and organization?
3. Sufficient depth of analysis?

Rate 1-10 for completeness."""

        response = self.llm.invoke(prompt)
        return {
            'check': 'completeness',
            'response': strip_think_tags(response.content)
        }

    def check_accuracy_credibility(self, markdown: str, findings: list[str]) -> dict[str, Any]:
        """Evaluate claims and credibility"""
        findings_text = '\n'.join(f'- {f}' for f in findings)

        prompt = f"""Review these research findings for credibility and logical consistency:

{findings_text}

Are the findings:
1. Well-supported and logical?
2. Free of obvious contradictions?
3. Properly qualified and nuanced?

Provide assessment with any concerns."""

        response = self.llm.invoke(prompt)
        return {
            'check': 'credibility',
            'response': strip_think_tags(response.content)
        }

    def check_clarity(self, markdown: str) -> dict[str, Any]:
        """Check writing clarity and readability"""
        prompt = f"""Evaluate the clarity and readability of this report excerpt:

{markdown[:1500]}

Rate clarity 1-10 and identify:
1. Any confusing sections
2. Unclear language or jargon
3. Suggestions for improvement"""

        response = self.llm.invoke(prompt)
        return {
            'check': 'clarity',
            'response': strip_think_tags(response.content)
        }

    def identify_gaps(self, markdown: str, topic: str) -> list[str]:
        """Identify gaps in coverage"""
        prompt = f"""What important aspects of "{topic}" might be missing from this report?

{markdown[:2000]}

List potential gaps or areas that need deeper exploration (be specific)."""

        response = self.llm.invoke(prompt)
        clean = strip_think_tags(response.content)
        gaps = [g.strip() for g in clean.split('\n') if g.strip()]

        if not gaps:
            logger.warning("No gaps identified after stripping think tags.")

        return gaps[:5]

    def generate_feedback(self, topic: str, issues: list[str],
                          gaps: list[str]) -> str:
        """Generate comprehensive feedback"""
        issues_text = '\n'.join(f'- {i}' for i in issues)
        gaps_text = '\n'.join(f'- {g}' for g in gaps)

        prompt = f"""Generate constructive feedback for improving a research report on "{topic}".

Current Issues:
{issues_text}

Coverage Gaps:
{gaps_text}

Provide 2-3 paragraphs of actionable feedback."""

        response = self.llm.invoke(prompt)
        return strip_think_tags(response.content)

    def determine_pass(self, reviews: list[dict], issues: list[str]) -> bool:
        """Determine if report passes review"""
        # Strip think tags from review responses before checking for 'critical'
        has_critical_issues = any(
            'critical' in strip_think_tags(str(r)).lower() for r in reviews
        )
        too_many_gaps = len(issues) > 5

        return not has_critical_issues and not too_many_gaps

    def review(self, topic: str, markdown: str, key_findings: list[str]) -> CriticReview:
        """Main review workflow"""
        logger.info(f"Starting review for topic: {topic}")

        completeness = self.check_completeness(markdown, topic)
        credibility = self.check_accuracy_credibility(markdown, key_findings)
        clarity = self.check_clarity(markdown)
        gaps = self.identify_gaps(markdown, topic)

        issues = [
            "Potential completeness concerns detected",
            "Clarity can be improved in places",
        ] + gaps[:3]

        feedback = self.generate_feedback(topic, issues, gaps)
        score = max(70, 100 - (len(issues) * 8) - (len(gaps) * 5))
        passed = self.determine_pass([completeness, credibility, clarity], gaps)

        logger.info(f"Review complete. Score: {score}, Passed: {passed}")

        return CriticReview(
            passed_review=passed,
            issues=issues,
            feedback=feedback,
            improvement_areas=gaps,
            overall_score=min(100, score)
        )
