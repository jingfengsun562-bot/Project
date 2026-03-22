"""
main.py — Monthly Investment Outlook Agent
CLI entry point.

Usage:
    python main.py
    python main.py --output-dir reports
    python main.py --url-file path/to/urls.txt
"""

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

import agent
import scraper
import report


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate a monthly investment outlook PDF report."
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Directory to save the PDF report (default: output/)",
    )
    parser.add_argument(
        "--url-file",
        default="Investment_Outlook_url.txt",
        help="Path to file containing investment outlook URLs (default: Investment_Outlook_url.txt)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    load_dotenv()

    url_file = args.url_file
    if not Path(url_file).exists():
        print(f"[ERROR] URL file not found: {url_file}")
        sys.exit(1)

    print("=" * 60)
    print("  Monthly Investment Outlook Agent")
    print("=" * 60)

    # Step 1: Fetch all sources (pure Python, zero AI tokens)
    sources = scraper.fetch_all(url_file)

    if not sources:
        print("\n[ERROR] No content fetched from any source. Check your internet connection.")
        sys.exit(1)

    print(f"\n[Scraper] Total sources with content: {len(sources)}")

    # Step 2: Synthesize with Claude (single API call)
    data = agent.synthesize(sources)

    # Step 3: Generate branded PDF
    print("\n[Report] Generating PDF...")
    output_path = report.generate_pdf(data, output_dir=args.output_dir)

    print("\n" + "=" * 60)
    print(f"  Report saved: {output_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
