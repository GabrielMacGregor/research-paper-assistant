"""Download arXiv papers as PDFs to data/papers/."""

import json
import time
from pathlib import Path

import requests
from tqdm import tqdm

PAPERS_METADATA_PATH = Path("data/papers_metadata.json")
OUTPUT_DIR = Path("data/papers")
ARXIV_PDF_URL = "https://arxiv.org/pdf/{arxiv_id}.pdf"
RATE_LIMIT_SECONDS = 3


def download_paper(arxiv_id: str, output_dir: Path) -> Path | None:
    output_path = output_dir / f"{arxiv_id}.pdf"
    if output_path.exists() and output_path.stat().st_size > 1000:
        return output_path

    url = ARXIV_PDF_URL.format(arxiv_id=arxiv_id)
    try:
        response = requests.get(
            url,
            stream=True,
            timeout=60,
            headers={"User-Agent": "RAG-Research-Assistant/1.0 (educational use)"},
        )
        response.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return output_path
    except requests.RequestException as e:
        print(f"  ERROR downloading {arxiv_id}: {e}")
        return None


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(PAPERS_METADATA_PATH) as f:
        papers = json.load(f)

    print(f"Downloading {len(papers)} papers to {OUTPUT_DIR}/")
    print("Rate limited to 1 request every 3s to be polite to arXiv.\n")

    success, failed = 0, []

    for paper in tqdm(papers, desc="Downloading"):
        arxiv_id = paper["arxiv_id"]
        result = download_paper(arxiv_id, OUTPUT_DIR)
        if result:
            success += 1
        else:
            failed.append(arxiv_id)
        time.sleep(RATE_LIMIT_SECONDS)

    print(f"\nDone: {success}/{len(papers)} downloaded successfully.")
    if failed:
        print(f"Failed IDs: {failed}")
        print("Tip: retry failed papers manually or check the arXiv ID.")


if __name__ == "__main__":
    main()
