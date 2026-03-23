Multi-Agent Autonomous Research Assistant
This project is a sophisticated multi-agent orchestration system designed to transform a single research topic into a comprehensive, high-quality Markdown and PDF report. Built with LangGraph, the system utilizes a modular architecture where specialized AI agents collaborate, critique, and refine information autonomously while keeping the user in the loop for critical decision-making.

Core Architecture & Workflow
The system leverages a 4-agent pipeline to ensure depth and accuracy:

Research Agent: Performs deep-web harvesting using the Tavily API to gather the most relevant and up-to-date data.

Analysis Agent: Synthesizes raw data, identifying key trends and technical insights.

Writer Agent: Drafts a structured, professional report based on the synthesized findings.

Critic Agent: Acts as the quality gate, reviewing the draft for gaps or inconsistencies and routing it back for revisions if necessary.

Key Features
Human-in-the-Loop (HITL): Implements a strategic pause before the final writing phase, allowing users to approve or provide feedback on the research direction.

Stateful Orchestration: Powered by LangGraph, the system manages complex state transitions and recursive feedback loops between agents.

High-Performance Backend: Built with FastAPI and integrated with the Sarvam API for localized, high-speed LLM processing.

Seamless UI: A clean interface where users can input topics, track agent progress in real-time, and download the final output as a PDF.

This repository showcases a production-ready approach to Agentic Workflows, balancing total autonomy with human oversight to solve complex information-gathering tasks.

