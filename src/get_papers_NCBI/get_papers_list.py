#!/usr/bin/env python3
"""
Command-line interface for the PubMed Fetcher.
Searches PubMed for papers with non-academic authors and extracts relevant details.
"""

import argparse
import logging
import sys
from typing import Optional

from .pubmed_fetcher import PubMedFetcher


def main() -> None:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Search PubMed for papers with non-academic authors and extract relevant details."
    )

    parser.add_argument(
        "query", 
        nargs="?", 
        help="Search query for PubMed."
    )
    parser.add_argument(
        "-d", "--debug", 
        action="store_true", 
        help="Enable debug logging."
    )
    parser.add_argument(
        "-f", "--file", 
        type=str, 
        help="Output filename (CSV). If not provided, results will be printed to console."
    )
    parser.add_argument(
        "-m", "--max", 
        type=int, 
        default=20, 
        help="Maximum number of results to fetch (default: 20)"
    )
    parser.add_argument(
        "-k", "--api-key",
        type=str,
        help="NCBI API key. If not provided, will use default key."
    )

    args: argparse.Namespace = parser.parse_args()

    # Set logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.debug("Debug mode is enabled")

    # Check for query
    if not args.query:
        logging.error("No query provided. Use -h for help.")
        sys.exit(1)

    # Use provided API key or default
    api_key: str = args.api_key or "6f26a8573bb6248f570994bba6d54c92b708"
    
    # Validate max results
    max_results: int = max(1, args.max) if args.max else 20

    try:
        # Create fetcher instance
        fetcher: PubMedFetcher = PubMedFetcher(
            query=args.query,
            api_key=api_key,
            max_results=max_results
        )

        # Fetch data
        logging.info(f"Searching for papers with query: '{args.query}'")
        fetcher.fetch_pmids()
        fetcher.fetch_paper_details()

        # Output results
        if args.file:
            fetcher.save_to_csv(filename=args.file)
        else:
            fetcher.print_results()

    except KeyboardInterrupt:
        logging.info("Search interrupted by user")
        sys.exit(1)
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        if args.debug:
            logging.exception("Full error traceback:")
        sys.exit(1)


if __name__ == "__main__":
    main()



# Sample Command
# python -m poetry run get-papers-list "psychedelic therapy"
# python -m poetry run get-papers-list "psychedelic therapy" -f results.csv -m 50