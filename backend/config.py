"""Application configuration from environment variables."""
import os


class Config:
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "5566"))
    DB_NAME = os.getenv("DB_NAME", "ghostbusters")
    DB_USER = os.getenv("DB_USER", "ghostbusters")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "ghostbusters_dev")
    FLASK_PORT = int(os.getenv("FLASK_PORT", "8066"))
    MCP_PORT = int(os.getenv("MCP_PORT", "8067"))
    AI_PROVIDER = os.getenv("AI_PROVIDER", "claude")


config = Config()
