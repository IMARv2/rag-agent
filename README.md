# RAG Agent

Personal local AI agent with semantic document search and chat interface.

## Stack
- **Backend**: FastAPI + ChromaDB + watchdog + pdfplumber
- **Embeddings**: nomic-embed-text (via Ollama)
- **LLMs**: qwen2.5:14b (chat), deepseek-r1:14b (reasoning), qwen2.5-coder:14b (code)
- **Frontend**: Single-page HTML/JS chat UI

## Features
- Semantic search across private documents (PDF, text)
- Multi-tool agent loop (search, read, summarize, list files)
- Auto-indexing via file watcher (watchdog)
- Auth-protected web UI (session cookie)
- Systemd service integration

## Setup

### Requirements
- Python 3.11+
- Ollama running locally with nomic-embed-text and qwen2.5:14b pulled

### Install

    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env
    # Edit .env with your credentials

### Run

    uvicorn main:app --host 0.0.0.0 --port 8766

### Systemd Service

    sudo cp rag-agent.service /etc/systemd/system/
    sudo systemctl enable --now rag-agent

## Project Structure

    rag-agent/
    +-- main.py              # FastAPI app entry point
    +-- config.py            # Settings (reads from .env)
    +-- agent/
    |   +-- agent.py         # Agent loop + tool dispatch
    |   +-- tools.py         # Tool definitions
    +-- indexer/
    |   +-- indexer.py       # Document indexing + ChromaDB
    |   +-- parsers.py       # PDF/text parsers
    |   +-- watcher.py       # File watcher (auto-index)
    +-- static/
        +-- index.html       # Chat UI
        +-- login.html       # Login page

## Environment Variables
See .env.example for required variables.
