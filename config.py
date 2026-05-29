from pathlib import Path
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

_BASE = Path(__file__).parent

class Settings(BaseSettings):
    ollama_base_url: str = "http://localhost:11434"
    embed_model: str = "nomic-embed-text:latest"
    chat_model: str = "qwen2.5:14b"
    docs_path: str = str(_BASE / "docs")
    chroma_path: str = str(_BASE / "data" / "chroma")
    collection_name: str = "rag_docs"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    top_k: int = 5
    port: int = 8766
    secret_key: str = "change-me-in-dotenv"
    auth_user: str = "admin"
    auth_pass: str = "changeme"

settings = Settings()
