
IST 303 – XR Team Exercise #2
Fall 2025 | Due Nov 13, 2025 @ 10:00 PM

Overview
This project refactors the provided team_ex_2.py (naive Wikipedia downloader) to make it efficient, extendable, and user-friendly.
The refactored file is named team_ex_2_refactored.py.

The program downloads reference links from related Wikipedia pages for a given topic.
It supports sequential, threaded, and multiprocessing execution modes.

New Features Added
Feature	Description
User Input	Accepts a search term from the user via CLI (--term) or interactive prompt.
Fallback Rule	If input is fewer than 4 characters, defaults to "generative artificial intelligence".
Output Directory	Creates a new directory wiki_dl/ to store all downloaded .txt files.
Multiple Modes	Run sequentially, with threads, or with multiple processes (`--mode seq	threads	procs`).
Error Handling	Handles DisambiguationError, PageError, and network timeouts safely.
Safe Filenames	Sanitizes Wikipedia titles before saving (no invalid chars).
Limiting and Timing	--max flag limits number of pages; total run time printed in summary.
Documentation & CLI	Full argparse interface and help text for easier testing and grading.
Original Issues and Fixes
#	Issue Found	Fix Implemented
1	Hard-coded search term (no input flexibility)	Added --term argument and input prompt; added coerce_search_term() fallback.
2	Files saved in working directory	Introduced ensure_dir() to create and use wiki_dl/.
3	Duplicate logic across modes	Refactored into shared helpers (fetch_page_references, save_references, _process_worker).
4	No error handling	Added try/except around all Wikipedia API calls.
5	Filenames not sanitized	Implemented safe_filename() using regex cleanup and truncation.
6	Unlimited number of results	Added --max argument to limit wikipedia.search() output.
7	Nested worker functions unsafe for multiprocessing	Moved _process_worker() to top-level scope for pickling safety.
8	No CLI or documentation	Added argparse CLI, top-level docstring, and README documentation.
IS