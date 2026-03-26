# Architecture: Multi-Agent Research Assistant

## Overview

A FastAPI backend orchestrates four specialized AI agents powered by the Sarvam LLM API and Tavily web search. Users interact via a standalone HTML frontend. Each research request runs as a background task through a four-phase pipeline: Research → Analysis → Writing → Critique.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     CLIENT LAYER                        │
│                                                         │
│   index.html  (Vanilla JS, polls /research/status)      │
│   cli.py      (Command-line interface)                  │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP (port 8000)
┌──────────────────────▼──────────────────────────────────┐
│                   FASTAPI BACKEND                        │
│                     main.py                             │
│                                                         │
│   POST /research/start                                  │
│   GET  /research/status/{session_id}                    │
│   GET  /research/report/{session_id}                    │
│   GET  /research/download/{session_id}  → PDF           │
└──────────────────────┬──────────────────────────────────┘
                       │ BackgroundTask
┌──────────────────────▼──────────────────────────────────┐
│               ORCHESTRATION LAYER                        │
│                 orchestration.py                        │
│                                                         │
│   ResearchOrchestrator                                  │
│   ResearchState (Pydantic model)                        │
│                                                         │
│   Phase 1 → Phase 2 → Phase 3 → Phase 4                │
└───┬──────────────┬──────────────┬──────────────┬────────┘
    │              │              │              │
┌───▼───┐    ┌────▼────┐   ┌─────▼─────┐  ┌────▼─────┐
│Research│   │Analysis │   │  Writer   │  │  Critic  │
│ Agent │   │  Agent  │   │   Agent   │  │  Agent   │
└───┬───┘   └────┬────┘   └─────┬─────┘  └────┬─────┘
    │             │              │              │
    │        ┌────▼──────────────▼──────────────▼─────┐
    │        │           sarvam_wrapper.py             │
    │        │         SarvamLLM (sarvam-m)            │
    │        │      https://api.sarvam.ai/v1           │
    │        └────────────────────────────────────────┘
    │
┌───▼──────────────┐
│   Tavily Search  │
│  (Web Research)  │
└──────────────────┘
```

---

## Agent Pipeline

### Phase 1 — Research Agent (`agents/research_agent.py`)
- Receives the user's topic
- Calls SarvamLLM to generate 5 diverse search queries
- Executes each query via TavilyClient
- Returns `ResearchResult` containing all raw results and a summary

### Phase 2 — Analysis Agent (`agents/analysis_agent.py`)
- Takes raw search results from Phase 1
- Extracts 5–7 key findings using SarvamLLM
- Identifies 4–6 recurring themes
- Synthesizes a multi-paragraph analytical overview
- Returns `AnalysisResult`

### Phase 3 — Writer Agent (`agents/writer_agent.py`)
- Takes findings, themes, and analysis from Phase 2
- Generates four report sections in parallel calls to SarvamLLM:
  - Executive Summary
  - Detailed Findings
  - Methodology
  - Recommendations
- Assembles a complete Markdown document
- Returns `WriterResult` with the full markdown and section list

### Phase 4 — Critic Agent (`agents/critic_agent.py`)
- Reviews the draft report for completeness, credibility, and clarity
- Identifies coverage gaps
- Generates constructive feedback
- Produces an overall quality score (0–100)
- Returns `CriticReview` with pass/fail verdict

---

## Data Flow

```
User Input (topic)
      │
      ▼
ResearchAgent.research(topic)
      │  → generate_search_queries()  [Sarvam LLM]
      │  → search() × 5              [Tavily API]
      │
      ▼  ResearchResult { topic, queries, results{}, summary }
      │
AnalysisAgent.analyze(topic, results)
      │  → extract_key_findings()    [Sarvam LLM]
      │  → identify_themes()         [Sarvam LLM]
      │  → synthesize_analysis()     [Sarvam LLM]
      │
      ▼  AnalysisResult { key_findings[], themes[], analysis, data_points{} }
      │
WriterAgent.write_report(topic, findings, themes, analysis, results)
      │  → create_executive_summary()   [Sarvam LLM]
      │  → create_detailed_findings()   [Sarvam LLM]
      │  → create_methodology()         [Sarvam LLM]
      │  → create_recommendations()     [Sarvam LLM]
      │
      ▼  WriterResult { markdown, title, sections[] }
      │
CriticAgent.review(topic, markdown, key_findings)
      │  → check_completeness()         [Sarvam LLM]
      │  → check_accuracy_credibility() [Sarvam LLM]
      │  → check_clarity()              [Sarvam LLM]
      │  → identify_gaps()              [Sarvam LLM]
      │  → generate_feedback()          [Sarvam LLM]
      │
      ▼  CriticReview { passed_review, score, issues[], feedback }
      │
Final Report (Markdown) → utils.markdown_to_pdf() → StreamingResponse
```

---

## File Reference

| File | Purpose |
|------|---------|
| `main.py` | FastAPI app, routes, session state, background task runner |
| `orchestration.py` | `ResearchOrchestrator` — initializes all agents, defines `ResearchState` |
| `sarvam_wrapper.py` | HTTP wrapper around Sarvam API with retry logic |
| `agents/research_agent.py` | Web search + query generation |
| `agents/analysis_agent.py` | Findings extraction + theme identification |
| `agents/writer_agent.py` | Markdown report generation |
| `agents/critic_agent.py` | Quality review + scoring |
| `utils.py` | `markdown_to_pdf()` via ReportLab, `format_research_for_display()` |
| `exporter.py` | Multi-format export (MD, PDF, HTML, JSON) and ZIP packaging |
| `sessions.py` | `SessionManager` + `SessionCache` (built, not yet wired into main.py) |
| `metrics.py` | `MetricsCollector` for phase timing + quality tracking (built, not yet wired) |
| `cli.py` | Full CLI interface using argparse, calls orchestrator directly |
| `index.html` | Standalone HTML/JS frontend, polls FastAPI backend |
| `Dockerfile` | Python 3.11-slim image, exposes port 8000 |
| `docker-compose.yaml` | Single-service deployment with env vars and volume mounts |
| `start_ui.bat` | Windows dev launcher — starts uvicorn + opens index.html |

---

## External Dependencies

| Service | Used For | Key |
|---------|---------|-----|
| Sarvam AI (`api.sarvam.ai`) | LLM inference for all agents | `SARVAM_API_KEY` |
| Tavily | Web search in Research Agent | `TAVILY_API_KEY` |

---

## Session State

Sessions are stored in memory in `main.py` as a plain dict (`research_sessions`). Each session tracks:

```python
{
  "topic": str,
  "status": str,        # Starting → Research → Analysis → Writing → Review → Completed
  "progress": int,      # 0–100
  "error": str | None,
  "research_data": ResearchResult | None,
  "analysis_data": AnalysisResult | None,
  "draft_report":  WriterResult | None,
  "review_result": CriticReview | None,
  "final_report":  WriterResult | None,
}
```

> Note: `sessions.py` provides a full `SessionManager` with disk persistence and `SessionCache` — these are ready to be wired into `main.py` to replace the in-memory dict.

---

## Deployment

### Local (Windows)
```
start_ui.bat → uvicorn main:app on :8000 → opens index.html in browser
```

### Docker
```
docker-compose up --build
Backend available at http://localhost:8000
Open index.html manually in browser
```