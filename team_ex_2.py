"""
Team Exercise #2

What changed:
- Added user input (CLI and interactive) for search term with <4 chars fallback to default.
- Creates ./wiki_dl directory and saves all .txt files there.
- Consolidated shared logic (fetch & save) into reusable functions.
- Safer filename handling, basic logging, and robust error handling for Wikipedia exceptions.
- Supports three execution modes: sequential, threads, processes (select via --mode).
- Added --max results limiter and clear timing output.

Run examples:
  python team_ex_2_refactored.py --term "generative ai" --mode threads --max 12
  python team_ex_2_refactored.py --mode seq
  # If --term omitted, you'll be prompted; inputs <4 chars fall back to default

Requires:
  pip install wikipedia
"""
from __future__ import annotations

import argparse
import re
import time
import io
import os
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple

import wikipedia
from wikipedia.exceptions import DisambiguationError, PageError, HTTPTimeoutError

# Global settings
DEFAULT_TERM = "generative artificial intelligence"
OUTPUT_DIR = Path("wiki_dl")
MAX_DEFAULT = 10

# Wikipedia library niceties
wikipedia.set_rate_limiting(True)


# ------------------------------ Utilities ------------------------------ #

def coerce_search_term(term: str | None) -> str:
    """Clean and validate the search term; fallback when <4 chars or empty."""
    if not term:
        return DEFAULT_TERM
    term = term.strip()
    if len(term) < 4:
        return DEFAULT_TERM
    return term


def ensure_dir(path: Path = OUTPUT_DIR) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_filename(name: str) -> str:
    """Make a filesystem-safe filename from a page title."""
    # Replace slashes and illegal characters, collapse spaces
    name = re.sub(r"[\\/:*?\"<>|]+", "_", name)
    name = re.sub(r"\s+", " ", name).strip()
    # Truncate to a reasonable length to avoid OS limits
    return (name[:150]).rstrip()


@dataclass
class FetchResult:
    title: str
    references: List[str]
    error: str | None = None


# --------------------------- Core operations --------------------------- #

def search_related(term: str, limit: int) -> List[str]:
    """Return related page titles for a term, limited to `limit`."""
    results = wikipedia.search(term) or []
    return results[:max(0, limit)]


def fetch_page_references(title: str) -> FetchResult:
    """Fetch a page and collect its references."""
    try:
        page = wikipedia.page(title, auto_suggest=False)
        refs = list(page.references or [])
        return FetchResult(title=page.title, references=refs)
    except DisambiguationError as e:
        return FetchResult(title=title, references=[], error=f"Disambiguation: {e}")
    except PageError as e:
        return FetchResult(title=title, references=[], error=f"PageError: {e}")
    except HTTPTimeoutError as e:
        return FetchResult(title=title, references=[], error=f"Timeout: {e}")
    except Exception as e:  # catch-all so one bad page doesn't halt the run
        return FetchResult(title=title, references=[], error=f"Unexpected: {e}")


def save_references(result: FetchResult, outdir: Path) -> Path | None:
    if result.error is not None:
        return None
    fn = safe_filename(result.title) + ".txt"
    path = outdir / fn
    text = "\n".join(result.references)
    path.write_text(text, encoding="utf-8")
    return path


# -------------------------- Execution strategies ---------------------- #

def run_sequential(titles: Iterable[str], outdir: Path) -> Tuple[int, int]:
    ok = 0
    skipped = 0
    for t in titles:
        res = fetch_page_references(t)
        p = save_references(res, outdir)
        if p:
            ok += 1
            print(f"✓ wrote {p.name}")
        else:
            skipped += 1
            print(f"– skipped {t} ({res.error})")
    return ok, skipped


def _process_worker(title: str, outdir: str) -> Tuple[str, str | None]:
    """Top-level worker for ProcessPool; returns (filename or title, error)."""
    res = fetch_page_references(title)
    if res.error is not None:
        return (title, res.error)
    p = save_references(res, Path(outdir))
    return (p.name if p else title, None)


def run_threads(titles: Iterable[str], outdir: Path, max_workers: int | None = None) -> Tuple[int, int]:
    ok = 0
    skipped = 0
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(_process_worker, t, str(outdir)): t for t in titles}
        for fut in as_completed(futures):
            title = futures[fut]
            try:
                name_or_title, err = fut.result()
                if err is None:
                    ok += 1
                    print(f"✓ wrote {name_or_title}")
                else:
                    skipped += 1
                    print(f"– skipped {title} ({err})")
            except Exception as e:
                skipped += 1
                print(f"– skipped {title} (thread error: {e})")
    return ok, skipped


def run_processes(titles: Iterable[str], outdir: Path, max_workers: int | None = None) -> Tuple[int, int]:
    ok = 0
    skipped = 0
    with ProcessPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(_process_worker, t, str(outdir)): t for t in titles}
        for fut in as_completed(futures):
            title = futures[fut]
            try:
                name_or_title, err = fut.result()
                if err is None:
                    ok += 1
                    print(f"✓ wrote {name_or_title}")
                else:
                    skipped += 1
                    print(f"– skipped {title} ({err})")
            except Exception as e:
                skipped += 1
                print(f"– skipped {title} (process error: {e})")
    return ok, skipped


# ------------------------------- CLI ---------------------------------- #

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Download Wikipedia reference links for related pages.")
    p.add_argument("--term", type=str, default=None, help="Search term (prompted if omitted).")
    p.add_argument("--mode", choices=["seq", "threads", "procs"], default="seq", help="Execution mode.")
    p.add_argument("--max", type=int, default=MAX_DEFAULT, help="Max number of related pages to process.")
    p.add_argument("--workers", type=int, default=None, help="Max workers for threads/processes (optional).")
    p.add_argument("--outdir", type=Path, default=OUTPUT_DIR, help="Output directory (default: ./wiki_dl)")
    return p.parse_args()


def main():
    args = parse_args()

    # Prompt if needed, then enforce fallback rule
    term = args.term or input("Enter a search term: ")
    term = coerce_search_term(term)

    outdir = ensure_dir(args.outdir)

    print(f"Searching Wikipedia for related pages to: '{term}'")
    titles = search_related(term, args.max)
    if not titles:
        print("No related pages found. Nothing to do.")
        return

    print(f"Processing {len(titles)} page(s) → saving .txt files to {outdir.resolve()}\n")

    t0 = time.perf_counter()
    if args.mode == "seq":
        ok, skipped = run_sequential(titles, outdir)
    elif args.mode == "threads":
        ok, skipped = run_threads(titles, outdir, args.workers)
    else:
        ok, skipped = run_processes(titles, outdir, args.workers)
    t1 = time.perf_counter()

    print("\nSummary:")
    print(f"  wrote:   {ok}")
    print(f"  skipped: {skipped}")
    print(f"  elapsed: {t1 - t0:.2f} s")


if __name__ == "__main__":
    main()
