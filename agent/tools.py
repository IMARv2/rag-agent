import os
from pathlib import Path
from typing import List, Dict, Any
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from indexer.indexer import search_docs
from indexer.parsers import parse_file
from config import settings

SUPPORTED_EXTS = {".pdf", ".txt", ".md", ".rst", ".csv"}

def tool_search(query: str, top_k: int = 5) -> List[Dict]:
    """Search documents semantically."""
    return search_docs(query, top_k)

def tool_read_file(rel_path: str) -> str:
    """Read full content of a file."""
    full_path = os.path.join(settings.docs_path, rel_path)
    if not os.path.exists(full_path):
        return f"File not found: {rel_path}"
    try:
        return parse_file(full_path)
    except Exception as e:
        return f"Error reading file: {e}"

def tool_summarize(rel_path: str) -> str:
    """Read file content for summarization (returns raw text, agent handles summary)."""
    return tool_read_file(rel_path)

def tool_list_files(subfolder: str = "", ext: str = "") -> List[str]:
    """List files in docs folder, optionally filtered by subfolder or extension."""
    base = Path(settings.docs_path)
    search_path = base / subfolder if subfolder else base
    if not search_path.exists():
        return []
    results = []
    for p in sorted(search_path.rglob("*")):
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS:
            if not ext or p.suffix.lower() == ext.lower():
                results.append(str(p.relative_to(base)))
    return results

TOOLS = {
    "search": {
        "fn": tool_search,
        "description": "Search documents semantically by query",
        "params": {"query": "str", "top_k": "int (optional, default 5)"}
    },
    "read_file": {
        "fn": tool_read_file,
        "description": "Read full content of a specific file",
        "params": {"rel_path": "str (relative to docs root)"}
    },
    "summarize": {
        "fn": tool_summarize,
        "description": "Get content of a file for summarization",
        "params": {"rel_path": "str (relative to docs root)"}
    },
    "list_files": {
        "fn": tool_list_files,
        "description": "List available files, optionally filtered",
        "params": {"subfolder": "str (optional)", "ext": "str (optional, e.g. .pdf)"}
    }
}
