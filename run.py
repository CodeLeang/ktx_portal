from pathlib import Path
import sys
import os

# Add backend package directory so `from app import ...` keeps working.
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))

from app import create_app

app = create_app()

if __name__ == "__main__":
    # Allow enabling debug/reloader and choosing port via environment variables.
    debug_env = os.environ.get("FLASK_DEBUG", "").lower()
    debug = True  # temporarily enabled for debugging
    port = int(os.environ.get("PORT", "5002"))
    app.run(host="0.0.0.0", port=port, debug=debug, use_reloader=debug)