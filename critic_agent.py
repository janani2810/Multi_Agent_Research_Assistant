from typing import Any
from sarvam_wrapper import SarvamLLM
from pydantic import BaseModel
from agents.research_agent import strip_think_tags
import re
import os
import logging
from concurrent.futures import ThreadPoolExecutor

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

End your response with exactly: "Completeness score: X/10" where X is your rating."""

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

Provide your assessment and end with exactly: "Credibility score: X/10" where X is your rating."""

        response = self.llm.invoke(prompt)
        return {
            'check': 'credibility',
            'response': strip_think_tags(response.content)
        }

    def check_clarity(self, markdown: str) -> dict[str, Any]:
        """Check writing clarity and readability"""
        prompt = f"""Evaluate the clarity and readability of this report excerpt:

{markdown[:1500]}

Identify:
1. Any confusing sections
2. Unclear language or jargon
3. Suggestions for improvement

End your response with exactly: "Clarity score: X/10" where X is your rating."""

        response = self.llm.invoke(prompt)
        return {
            'check': 'clarity',
            'response': strip_think_tags(response.content)
        }

    def identify_gaps(self, markdown: str, topic: str) -> list[str]:
        """Identify gaps in coverage"""
        prompt = f"""What important aspects of "{topic}" might be missing from this report?

{markdown[:2000]}

List potential gaps or areas that need deeper exploration (be specific).
Return only the gaps, one per line, no numbering."""

        response = self.llm.invoke(prompt)
        clean = strip_think_tags(response.content)
        gaps = [g.strip() for g in clean.split('\n') if g.strip()]

        if not gaps:
            logger.warning("No gaps identified after stripping think tags.")

        return gaps[:5]

    def generate_feedback(self, topic: str, issues: list[str], gaps: list[str]) -> str:
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

    def determine_pass(self, reviews: list[dict], gaps: list[str]) -> bool:
        """Determine if report passes review"""
        has_critical_issues = any(
            'critical' in strip_think_tags(str(r)).lower() for r in reviews
        )
        too_many_gaps = len(gaps) > 5
        return not has_critical_issues and not too_many_gaps

    @staticmethod
    def extract_score(text: str) -> int:
        """
        Extract a 1-10 rating from LLM response text.

        Priority order:
          1. Explicit keyword patterns: "Completeness score: 8/10", "rating: 7", etc.
          2. Bare "X/10" pattern anywhere in the text.
          3. Standalone digit 6-10 not part of a range like "1-10".
          4. Default neutral score of 65 if nothing found.
        """
        # Priority 1: keyword + number (with optional /10)
        explicit = re.findall(
            r'(?:score|rating|rate|completeness|clarity|credibility)[^\d]{0,10}(\d+)\s*(?:/\s*10)?',
            text, re.IGNORECASE
        )
        if explicit:
            val = int(explicit[0])
            if 1 <= val <= 10:
                return val * 10

        # Priority 2: "X/10" anywhere
        slash_ten = re.findall(r'\b(\d+)\s*/\s*10\b', text)
        if slash_ten:
            val = int(slash_ten[0])
            if 1 <= val <= 10:
                return val * 10

        # Priority 3: standalone 6-10 not inside a range (e.g. not "1-10")
        standalone = re.findall(r'(?<![-\d])([6-9]|10)(?![-\d/])', text)
        if standalone:
            val = int(standalone[0])
            return val * 10

        # Default: neutral score
        return 65

    def review(self, topic: str, markdown: str, key_findings: list[str]) -> CriticReview:
        """Main review workflow — parallel LLM calls for speed"""
        logger.info(f"Starting review for topic: {topic}")

        # Run all four checks in parallel (they are fully independent)
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_completeness = executor.submit(self.check_completeness, markdown, topic)
            future_credibility  = executor.submit(self.check_accuracy_credibility, markdown, key_findings)
            future_clarity      = executor.submit(self.check_clarity, markdown)
            future_gaps         = executor.submit(self.identify_gaps, markdown, topic)

            completeness = future_completeness.result()
            credibility  = future_credibility.result()
            clarity      = future_clarity.result()
            gaps         = future_gaps.result()

        # Build issues list
        issues = [
            "Potential completeness concerns detected",
            "Clarity can be improved in places",
        ] + gaps[:3]

        # Generate feedback (depends on gaps, so runs after)
        feedback = self.generate_feedback(topic, issues, gaps)

        # Extract numeric scores from LLM responses
        completeness_score = self.extract_score(completeness['response'])
        credibility_score  = self.extract_score(credibility['response'])
        clarity_score      = self.extract_score(clarity['response'])

        logger.info(
            f"Parsed scores — completeness: {completeness_score}, "
            f"credibility: {credibility_score}, clarity: {clarity_score}"
        )

        # Weighted average with gap penalty
        raw_score = (
            completeness_score * 0.40 +
            credibility_score  * 0.35 +
            clarity_score      * 0.25
        )
        gap_penalty = len(gaps) * 3
        score = max(10, min(100, int(raw_score - gap_penalty)))

        passed = self.determine_pass([completeness, credibility, clarity], gaps)
        logger.info(f"Review complete. Score: {score}/100, Passed: {passed}")

        return CriticReview(
            passed_review=passed,
            issues=issues,
            feedback=feedback,
            improvement_areas=gaps,
            overall_score=score
        )
