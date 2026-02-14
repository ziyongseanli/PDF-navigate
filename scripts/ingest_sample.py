from __future__ import annotations

import argparse

import requests


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest a sample PDF into PDF Navigator")
    parser.add_argument("pdf_path", help="Path to local PDF")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    with open(args.pdf_path, "rb") as f:
        resp = requests.post(f"{args.base_url}/api/upload", files={"file": f})
    resp.raise_for_status()
    print(resp.json())


if __name__ == "__main__":
    main()
