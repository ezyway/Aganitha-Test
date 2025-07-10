# PubMed Company Paper Fetcher

A Python tool to search PubMed and identify research papers authored by individuals affiliated with pharmaceutical, biotech, or other commercial companies.

This command-line utility allows you to run a search query against the PubMed database and filters the results to find papers where at least one author's affiliation appears to be a non-academic, commercial entity.

## Features

- **PubMed Search**: Use any standard PubMed query to find relevant papers.
- **Intelligent Filtering**: Identifies company affiliations using a combination of:
  - Keywords common in biotech/pharma company names (e.g., `therapeutics`, `biopharma`).
  - Legal entity suffixes (e.g., `Inc`, `Ltd`, `GmbH`).
  - A curated list of known pharmaceutical and biotech companies.
- **Exclusion Logic**: Filters out common academic and research institutions (e.g., `University`, `Hospital`, `Institute`).
- **Flexible Output**: Print results directly to the console or save them in a structured CSV file.
- **Configurable**: Control the maximum number of results and provide your own NCBI API key.

## Installation

This project uses Poetry for dependency management.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/Aganitha-Test.git
    cd Aganitha-Test
    ```

2.  **Install dependencies using Poetry:**
    ```bash
    poetry install
    ```

## Usage

The tool is run from the command line using the `get-papers-list` script.

### Command-Line Interface

The basic command structure is:

```bash
poetry run get-papers-list "your search query" [options]
```

#### **Arguments:**

- `query`: (Required) The search term for PubMed, enclosed in quotes.
- `-f, --file`: The filename for the output CSV. If not provided, results are printed to the console.
- `-m, --max`: The maximum number of papers with company affiliations to fetch. (Default: `20`)
- `-k, --api-key`: Your personal NCBI API key. Recommended for extensive use.
- `-d, --debug`: Enable debug-level logging for detailed output.

### Examples

1.  **Basic search, print to console:**
    ```bash
    poetry run get-papers-list "psychedelic therapy"
    ```

2.  **Search and save 50 results to a CSV file:**
    ```bash
    poetry run get-papers-list "mrna vaccine development" -m 50 -f vaccine_papers.csv
    ```

3.  **Using a personal NCBI API key:**
    ```bash
    poetry run get-papers-list "monoclonal antibody" --api-key YOUR_NCBI_API_KEY
    ```

### Using as a Library

You can also import and use the `PubMedFetcher` class directly in your Python code for more programmatic control.

```python
from get_papers_NCBI import PubMedFetcher

# 1. Initialize the fetcher with your query and credentials
fetcher = PubMedFetcher(
    query="crispr gene editing",
    api_key="YOUR_NCBI_API_KEY", # It's best to use your own key
    max_results=10
)

# 2. Run the fetch and filter process
fetcher.fetch_pmids()
fetcher.fetch_paper_details()

# 3. Get the results as a list of dictionaries
papers = fetcher.get_results()

for paper in papers:
    print(paper['Title'])

# Or save directly to a CSV file
fetcher.save_to_csv("crispr_papers.csv")
```

## How It Works

The script follows a multi-step process to find relevant papers:

1.  **ESearch**: It first queries the PubMed `ESearch` API with your search term. To ensure enough candidates for filtering, it fetches a large number of PubMed IDs (PMIDs)—five times the `max_results` value.
2.  **EFetch**: It then processes these PMIDs in batches, calling the `EFetch` API to retrieve detailed metadata for each paper, including author names and affiliations.
3.  **Affiliation Filtering**: For each paper, it iterates through the authors' affiliations. An affiliation is considered "non-academic" or "commercial" if it:
    - Contains a known company name (e.g., `Pfizer`, `Moderna`).
    - Contains a business keyword (e.g., `therapeutics`, `biotech`).
    - Contains a legal entity suffix (e.g., `Inc.`, `Ltd.`).
    - AND does **not** contain an academic keyword (e.g., `University`, `Institute`).
4.  **Collection**: If a paper has at least one author with a company affiliation, its details are collected. The process stops once the `max_results` target is reached or all initial PMIDs have been processed.

## NCBI API Key

The NCBI E-utilities APIs have rate limits for users without an API key. While this script includes a default key for convenience, it is highly recommended that you **obtain your own free API key** for any serious or frequent use. This provides you with a much higher request rate.

You can get your key from your NCBI account settings:
**NCBI Account Settings - API Key Management**

Pass your key using the `-k` or `--api-key` argument.