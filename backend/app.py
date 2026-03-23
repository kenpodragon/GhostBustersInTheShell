"""GhostBusters In The Shell - Backend Application Entry Point

Flask API + MCP Server (SSE transport) in a single process.
MCP runs in a background daemon thread.
"""
import argparse
import threading
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

from config import config
from db import init_pool

app = Flask(__name__)
CORS(app)


# --- Health Check ---
@app.route("/api/health", methods=["GET"])
def health():
    from db import query_one
    try:
        row = query_one("SELECT 1 AS ok")
        return {"status": "healthy", "db": "connected"}, 200
    except Exception as e:
        return {"status": "unhealthy", "db": str(e)}, 503


# --- Register Blueprints ---
from routes.analyze import analyze_bp
from routes.rewrite import rewrite_bp
from routes.documents import documents_bp
from routes.voice_profiles import voice_profiles_bp
from routes.settings import settings_bp

app.register_blueprint(analyze_bp, url_prefix="/api")
app.register_blueprint(rewrite_bp, url_prefix="/api")
app.register_blueprint(documents_bp, url_prefix="/api")
app.register_blueprint(voice_profiles_bp, url_prefix="/api")
app.register_blueprint(settings_bp, url_prefix="/api")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-mcp", action="store_true", help="Skip MCP server")
    parser.add_argument("--mcp-port", type=int, default=config.MCP_PORT)
    args = parser.parse_args()

    # Initialize DB pool
    init_pool()

    # AI provider startup health check
    from ai_providers.router import startup_health_check
    startup_health_check()

    # Start MCP server in background thread
    if not args.no_mcp:
        def run_mcp():
            from mcp_server import mcp as mcp_instance
            mcp_instance.settings.host = "0.0.0.0"
            mcp_instance.settings.port = args.mcp_port
            print(f"[MCP] SSE server starting on port {args.mcp_port}")
            mcp_instance.run(transport="sse")

        mcp_thread = threading.Thread(target=run_mcp, daemon=True)
        mcp_thread.start()

    # Start Flask
    print(f"[Flask] API starting on port {config.FLASK_PORT}")
    app.run(host="0.0.0.0", port=config.FLASK_PORT, debug=False)


if __name__ == "__main__":
    main()
