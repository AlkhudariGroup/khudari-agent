from waitress import serve
from main import app
import os

if __name__ == "__main__":
    port = int(os.environ.get("HTTP_PORT", 5899))
    print(f"Starting Waitress server on port {port}...")
    serve(app, host='0.0.0.0', port=port)
