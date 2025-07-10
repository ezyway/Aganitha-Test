"""
PubMed Fetcher Package

A Python package for fetching research papers from PubMed that have authors
affiliated with pharmaceutical or biotech companies.
"""

from .pubmed_fetcher import PubMedFetcher

__version__ = "0.1.0"
__all__ = ["PubMedFetcher"]