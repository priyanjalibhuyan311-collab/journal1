import os
from dotenv import load_dotenv

from app import app, BASE_DIR

load_dotenv(os.path.join(BASE_DIR, ".env"))

if __name__ == "__main__":
    from waitress import serve

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5000"))
    serve(app, host=host, port=port)
