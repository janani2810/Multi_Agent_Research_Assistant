"""Utility functions for report generation and export"""

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
import markdown
from io import BytesIO
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def markdown_to_html(markdown_text: str) -> str:
    """Convert markdown to HTML"""
    return markdown.markdown(markdown_text)


def markdown_to_pdf(markdown_text: str, title: str) -> BytesIO:
    """Convert markdown report to PDF"""
    try:
        # Parse markdown
        lines = markdown_text.split('\n')
        
        # Create PDF
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(
            pdf_buffer,
            pagesize=letter,
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch
        )
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1f4788'),
            spaceAfter=30,
            alignment=TA_CENTER,
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#2e5c8a'),
            spaceAfter=12,
            spaceBefore=12,
        )
        
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontSize=10,
            alignment=TA_JUSTIFY,
            spaceAfter=12,
            leading=14,
        )
        
        # Build content
        content = []
        
        # Add title
        content.append(Paragraph(title, title_style))
        content.append(Spacer(1, 0.2 * inch))
        
        # Add metadata
        metadata = f"Generated: {datetime.now().strftime('%B %d, %Y at %H:%M:%S')}"
        content.append(Paragraph(metadata, styles['Normal']))
        content.append(Spacer(1, 0.3 * inch))
        
        # Process markdown lines
        for line in lines:
            line = line.strip()
            
            if not line:
                content.append(Spacer(1, 0.1 * inch))
            elif line.startswith('# '):
                content.append(Paragraph(line[2:], title_style))
                content.append(Spacer(1, 0.1 * inch))
            elif line.startswith('## '):
                content.append(Paragraph(line[3:], heading_style))
            elif line.startswith('### '):
                content.append(Paragraph(line[4:], styles['Heading3']))
            elif line.startswith('- '):
                # Bullet points
                content.append(Paragraph('• ' + line[2:], body_style))
            elif line.startswith('* '):
                content.append(Paragraph('• ' + line[2:], body_style))
            else:
                content.append(Paragraph(line, body_style))
        
        # Add footer
        content.append(Spacer(1, 0.2 * inch))
        content.append(Paragraph(
            "<i>This report was generated using AI-powered multi-agent research system.</i>",
            styles['Normal']
        ))
        
        # Build PDF
        doc.build(content)
        pdf_buffer.seek(0)
        logger.info("PDF generated successfully")
        return pdf_buffer
        
    except Exception as e:
        logger.error(f"PDF generation error: {str(e)}")
        raise


def save_markdown_file(markdown_text: str, filename: str) -> str:
    """Save markdown to file"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(markdown_text)
        logger.info(f"Markdown saved to {filename}")
        return filename
    except Exception as e:
        logger.error(f"Error saving markdown: {str(e)}")
        raise


def format_research_for_display(state: dict, session_id: str = None) -> dict:
    """Format research state for API response"""
    # Handle review_result which might be a Pydantic model
    review_result = state.get('review_result')
    review_score = None
    if review_result:
        # If it's a Pydantic model, access attributes directly
        if hasattr(review_result, 'overall_score'):
            review_score = review_result.overall_score
        # If it's a dict, use .get()
        elif isinstance(review_result, dict):
            review_score = review_result.get('overall_score')
    
    return {
        'session_id': session_id,
        'topic': state.get('topic'),
        'status': state.get('status'),
        'research_complete': state.get('research_data') is not None,
        'analysis_complete': state.get('analysis_data') is not None,
        'draft_ready': state.get('draft_report') is not None,
        'review_score': review_score,
        'final_ready': state.get('final_report') is not None,
        'error': state.get('error')
    }
