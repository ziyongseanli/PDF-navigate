from __future__ import annotations

import threading
import time

import uvicorn
import webview


def start_server() -> None:
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, log_level="info")


def main() -> None:
    thread = threading.Thread(target=start_server, daemon=True)
    thread.start()
    time.sleep(1)
    webview.create_window("PDF Navigator", "http://127.0.0.1:8000", width=1440, height=900)
    webview.start()


if __name__ == "__main__":
    main()
