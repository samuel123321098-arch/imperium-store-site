import threading
import subprocess
import os

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    from app import app
    app.run(host="0.0.0.0", port=port)

def run_bot():
    subprocess.run(["python", "main.py"])

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    run_bot()