#!/usr/bin/env python3
"""Command-line interface for the multi-agent research system"""
from dotenv import load_dotenv
import os
load_dotenv()

import sys
import argparse
import json
from pathlib import Path
from typing import Optional
import asyncio
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ResearchCLI:
    """Command-line interface for research system"""
    
    def __init__(self):
        """Initialize CLI"""
        self.parser = self._setup_parser()
    
    def _setup_parser(self) -> argparse.ArgumentParser:
        """Setup argument parser"""
        parser = argparse.ArgumentParser(
            description='Multi-Agent Research Assistant CLI',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog='''
Examples:
  research --topic "AI in healthcare" --output report.md
  research --topic "Climate solutions" --auto-approve --depth deep
  research --list-sessions
  research --status research_1234567890
            '''
        )
        
        # Subcommands
        subparsers = parser.add_subparsers(dest='command', help='Command to execute')
        
        # Research command
        research_parser = subparsers.add_parser(
            'research',
            help='Start a new research session'
        )
        research_parser.add_argument(
            '--topic', '-t',
            required=True,
            help='Research topic'
        )
        research_parser.add_argument(
            '--output', '-o',
            default=None,
            help='Output markdown file (default: stdout)'
        )
        research_parser.add_argument(
            '--pdf',
            action='store_true',
            help='Also generate PDF'
        )
        research_parser.add_argument(
            '--auto-approve',
            action='store_true',
            help='Auto-approve draft without manual review'
        )
        research_parser.add_argument(
            '--depth',
            choices=['quick', 'standard', 'deep', 'comprehensive'],
            default='standard',
            help='Research depth (default: standard)'
        )
        research_parser.add_argument(
            '--no-cache',
            action='store_true',
            help='Disable result caching'
        )
        research_parser.add_argument(
            '--watch',
            action='store_true',
            help='Watch progress in real-time'
        )
        
        # Status command
        status_parser = subparsers.add_parser(
            'status',
            help='Check session status'
        )
        status_parser.add_argument(
            'session_id',
            help='Session ID'
        )
        
        # List sessions command
        list_parser = subparsers.add_parser(
            'list',
            help='List recent sessions'
        )
        list_parser.add_argument(
            '--limit',
            type=int,
            default=10,
            help='Number of sessions to show (default: 10)'
        )
        
        # Statistics command
        stats_parser = subparsers.add_parser(
            'stats',
            help='Show system statistics'
        )
        
        # Configure command
        config_parser = subparsers.add_parser(
            'config',
            help='Manage configuration'
        )
        config_parser.add_argument(
            'action',
            choices=['show', 'reset', 'set'],
            help='Configuration action'
        )
        config_parser.add_argument(
            '--key',
            help='Config key (for set action)'
        )
        config_parser.add_argument(
            '--value',
            help='Config value (for set action)'
        )
        
        return parser
    
    def run(self, args: Optional[list] = None):
        """Run CLI"""
        parsed = self.parser.parse_args(args)
        
        if not parsed.command:
            self.parser.print_help()
            return
        
        try:
            if parsed.command == 'research':
                self.cmd_research(parsed)
            elif parsed.command == 'status':
                self.cmd_status(parsed)
            elif parsed.command == 'list':
                self.cmd_list(parsed)
            elif parsed.command == 'stats':
                self.cmd_stats(parsed)
            elif parsed.command == 'config':
                self.cmd_config(parsed)
        except Exception as e:
            logger.error(f"Error: {e}")
            sys.exit(1)
    
    def cmd_research(self, args):
        """Execute research command"""
        from orchestration import ResearchOrchestrator
        
        logger.info(f"🔍 Starting research: {args.topic}")
        logger.info(f"   Depth: {args.depth}, Auto-approve: {args.auto_approve}")
        
        # Initialize orchestrator
        orchestrator = ResearchOrchestrator()
        
        # Create session ID
        session_id = f"cli_{int(datetime.now().timestamp())}"
        
        # Run research
        print(f"\n📋 Session ID: {session_id}")
        print(f"⏱️  Estimated time: 2-3 minutes\n")
        
        try:
            # Phase 1: Research
            print("🔍 Phase 1: Researching...")
            research_data = orchestrator.research_agent.research(args.topic)
            print(f"   ✓ Found {len(research_data.results)} sources\n")
            
            # Phase 2: Analysis
            print("📊 Phase 2: Analyzing...")
            analysis_data = orchestrator.analysis_agent.analyze(
                args.topic,
                {q: r for q, r in zip(
                    research_data.queries,
                    [research_data.results.get(q, []) for q in research_data.queries]
                )}
            )
            print(f"   ✓ Extracted {len(analysis_data.key_findings)} findings")
            print(f"   ✓ Identified {len(analysis_data.themes)} themes\n")
            
            # Phase 3: Writing
            print("✍️  Phase 3: Writing...")
            draft_report = orchestrator.writer_agent.write_report(
                args.topic,
                analysis_data.key_findings,
                analysis_data.themes,
                analysis_data.analysis,
                research_data.results
            )
            print(f"   ✓ Generated {len(draft_report.sections)} report sections\n")
            
            # Phase 4: Critique
            print("🔍 Phase 4: Critiquing...")
            review = orchestrator.critic_agent.review(
                args.topic,
                draft_report.markdown,
                analysis_data.key_findings
            )
            print(f"   ✓ Quality score: {review.overall_score}/100\n")
            
            # Output
            if args.output:
                output_path = Path(args.output)
                output_path.write_text(draft_report.markdown, encoding='utf-8')
                print(f"📄 Report saved to: {output_path}")
            else:
                print("=" * 60)
                print(draft_report.markdown)
                print("=" * 60)
            
            # PDF export
            if args.pdf:
                from utils import markdown_to_pdf
                pdf_path = Path(args.output or "report").with_suffix(".pdf")
                pdf_buffer = markdown_to_pdf(draft_report.markdown, draft_report.title)
                pdf_path.write_bytes(pdf_buffer.getvalue())
                print(f"📑 PDF saved to: {pdf_path}")
            
            print(f"\n✅ Research complete!")
            
        except Exception as e:
            logger.error(f"Research failed: {e}", exc_info=True)
            sys.exit(1)
    
    def cmd_status(self, args):
        """Show session status"""
        print(f"Session ID: {args.session_id}")
        print("Status: Session management not enabled in CLI mode")
    
    def cmd_list(self, args):
        """List sessions"""
        print(f"Listing sessions (limit: {args.limit})")
        print("Sessions: CLI mode does not track sessions")
    
    def cmd_stats(self, args):
        """Show statistics"""
        print("Research System Statistics:")
        print("Run research with CLI to see stats")
    
    def cmd_config(self, args):
        """Manage configuration"""
        from config import get_config_manager
        
        manager = get_config_manager()
        
        if args.action == 'show':
            print(json.dumps(manager.current_config.dict(), indent=2, default=str))
        elif args.action == 'reset':
            manager.reset_to_defaults()
            manager.save_config()
            print("Configuration reset to defaults")
        elif args.action == 'set':
            if not args.key or not args.value:
                print("Error: --key and --value required for set action")
                sys.exit(1)
            # Would need more sophisticated parsing for nested values
            print(f"Setting {args.key} = {args.value}")


def main():
    """Main entry point"""
    cli = ResearchCLI()
    cli.run()


if __name__ == '__main__':
    main()
