# Multi_Agent_Reasearch_Assistant
This project is a sophisticated multi-agent orchestration system designed to transform a single research topic into a comprehensive, high-quality Markdown and PDF report. Built with LangGraph, the system utilizes a modular architecture where specialized AI agents collaborate,critique and refine information autonomously for critical decision-making.
An AI-powered research system that autonomously searches the web, analyzes findings, writes structured reports, and self-reviews quality — all through a pipeline of four specialized agents.

---

## How It Works

You enter a research topic. The system runs it through four agents in sequence:

1. **Research Agent** — generates search queries and gathers sources via Tavily
2. **Analysis Agent** — extracts key findings and identifies themes
3. **Writer Agent** — produces a structured Markdown report
4. **Critic Agent** — reviews quality and scores the report (0–100)

The final report is available as Markdown or PDF download.

---

## Project Structure

```
multi-agent-research-assistant/
│
├── agents/
│   ├── __init__.py
│   ├── research_agent.py
│   ├── analysis_agent.py
│   ├── writer_agent.py
│   └── critic_agent.py
│
├── tests/
│   └── tests.py
│
├── main.py               # FastAPI backend
├── orchestration.py      # Agent coordinator
├── sarvam_wrapper.py     # Sarvam LLM client
├── utils.py              # PDF generation, helpers
├── exporter.py           # Multi-format export
├── cli.py                # Command-line interface
│
├── index.html            # Frontend UI
│
├── Dockerfile
├── docker-compose.yaml
├── start_ui.bat          # Windows dev launcher
│
├── requirements.txt
├── .env.example
└── ARCHITECTURE.md
```

---

## Prerequisites

- Python 3.11+
- A [Sarvam AI](https://www.sarvam.ai) API key
- A [Tavily](https://tavily.com) API key

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/your-username/multi-agent-research-assistant.git
cd multi-agent-research-assistant
```

### 2. Create a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your keys:

```
SARVAM_API_KEY=your-sarvam-key-here
TAVILY_API_KEY=your-tavily-key-here
```

---

## Running the App

### Windows (easiest)

Double-click `start_ui.bat`. It will start the backend and open the UI in your browser automatically.

### Manual

```bash
# Start the backend
uvicorn main:app --reload --host 127.0.0.1 --port 8000

# Open index.html in your browser
# (just double-click it or open via file://)
```

Backend runs at `http://127.0.0.1:8000`

API docs available at `http://127.0.0.1:8000/docs`

### Docker

```bash
docker-compose up --build
```

Then open `index.html` in your browser manually.

---

## Using the CLI

```bash
# Run a research session
python cli.py research --topic "AI in healthcare" --output report.md

# Also export as PDF
python cli.py research --topic "Climate solutions" --output report.md --pdf

# Skip the draft approval step
python cli.py research --topic "Quantum computing" --auto-approve
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/research/start` | Start a new research session |
| `GET` | `/research/status/{session_id}` | Poll progress (0–100%) |
| `GET` | `/research/report/{session_id}` | Get markdown + quality score |
| `GET` | `/research/download/{session_id}` | Download PDF report |
| `GET` | `/health` | Health check |

### Start Research Request Body

```json
{
  "topic": "Your research topic here",
  "auto_approve": false
}
```

---

## Running Tests

```bash
pytest tests/tests.py -v
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SARVAM_API_KEY` | Yes | Sarvam AI API key |
| `TAVILY_API_KEY` | Yes | Tavily search API key |
| `LOG_LEVEL` | No | Logging level (default: `INFO`) |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | Sarvam AI (`sarvam-m`) |
| Web Search | Tavily |
| Backend | FastAPI + Uvicorn |
| PDF Generation | ReportLab |
| Frontend | Vanilla HTML/CSS/JS |
| Containerization | Docker + Docker Compose |

---

## Notes

- Research takes approximately 2–3 minutes per topic
- All sessions are stored in memory — restarting the server clears them
- `sessions.py` and `metrics.py` are built and ready to be integrated for persistent session storage and usage tracking
- The `exports/` directory is created automatically when using `exporter.py`
- The `reports/` directory stores output files and is mounted as a Docker volume
