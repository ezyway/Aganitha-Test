import requests
import xml.etree.ElementTree as ET
import argparse
import csv
import re
import time
import logging
import sys
from urllib.parse import quote_plus

# Configure logging with INFO level and a custom format
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class PubMedFetcher:
    """
    A class to fetch and filter PubMed papers based on author affiliations,
    specifically targeting commercial companies.
    """

    # Base URL for PubMed's E-utilities API
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

    # Keywords typically found in company names in the biotech/pharma industry
    COMPANY_KEYWORDS = [
        'biotech', 'biotechnology', 'therapeutics', 'sciences', 'solutions', 
        'technologies', 'biosciences', 'biopharma', 'biopharmaceuticals'
    ]

    # Common legal entity suffixes used in company names across countries
    LEGAL_ENTITIES = [
        'corp', 'corporation', 'company', 'inc', 'ltd', 'llc', 'llp',
        'gmbh', 'ag', 'sa', 'bv', 'nv', 'srl', 'spa', 'plc', 'pty',
        'co.', 'co ', ' co', 'limited', 'enterprises', 'holdings'
    ]

    # A curated list of known biotech and pharmaceutical companies for matching
    KNOWN_COMPANIES = [
        'pfizer', 'moderna', 'johnson', 'merck', 'roche', 'novartis',
        'sanofi', 'astrazeneca', 'gsk', 'glaxosmithkline', 'abbvie', 'biogen', 'amgen',
        'gilead', 'vertex', 'illumina', 'regeneron', 'celgene', 'bristol',
        'boehringer', 'takeda', 'bayer', 'eli lilly', 'lilly', 'abbott',
        'daiichi', 'sankyo', 'eisai', 'astellas', 'otsuka', 'shionogi',
        'chugai', 'sumitomo', 'mitsubishi', 'tanabe', 'kyowa', 'kirin',
        'alexion', 'incyte', 'biomarin', 'sarepta', 'bluebird', 'spark',
        'crispr', 'editas', 'intellia', 'sangamo', 'precision', 'exact',
        'foundation', 'guardant', 'veracyte', '10x genomics', 'twist',
        'pacific', 'seagen', 'immunomedics', 'macrogenics', 'nektar',
        'halozyme', 'dynavax', 'vaxcyte', 'novavax', 'cureVac', 'biontech',
        'alnylam', 'ionis', 'wave', 'dicerna', 'arrowhead', 'silence'
    ]

    # Terms commonly associated with academic or non-commercial institutions to exclude
    ACADEMIC_EXCLUSIONS = [
        'university', 'college', 'school', 'institute', 'hospital',
        'medical center', 'health system', 'research center', 'clinic',
        'academic', 'faculty', 'department', 'division', 'section',
        'laboratory', 'center for', 'centre for', 'research institute'
    ]

    def __init__(self, query, api_key, max_results=20):
        """
        Initialize the PubMedFetcher object.

        Parameters:
        query (str): PubMed search query.
        api_key (str): NCBI API key for accessing PubMed.
        max_results (int): Maximum number of papers to retrieve.
        """
        self.api_key = api_key               # API key for authentication and rate limits
        self.query = query                   # Search query to send to PubMed
        self.max_results = max_results       # Limit on number of results to fetch
        self.pmids = []                      # List to store PubMed IDs of matching papers
        self.papers_data = []                # Detailed information for each paper
        self.session = requests.Session()    # Reuse the session for efficient network calls


    def fetch_pmids(self):
        """
        Retrieve PubMed IDs (PMIDs) matching the query using the ESearch API.
        Fetch extra PMIDs to account for filtering non-company affiliations later.
        """
        search_query = self.query       # PubMed search term
        retmax = 100                    # Number of results to fetch per request
        retstart = 0                    # Offset for pagination

        # Keep fetching until we have enough PMIDs to allow for later filtering
        while len(self.pmids) < self.max_results * 5:
            params = {
                'db': 'pubmed',         # Database to search
                'term': search_query,   # Search term
                'retmax': retmax,       # Max results per API call
                'retstart': retstart,   # Offset for pagination
                'retmode': 'xml',       # Response format
                'api_key': self.api_key # API key for authentication
            }
            try:
                # Make the GET request to ESearch endpoint
                response = self.session.get(f"{self.BASE_URL}esearch.fcgi", params=params)
                response.raise_for_status()  # Raise exception for bad responses

                # Parse XML response and extract PMIDs
                root = ET.fromstring(response.content)
                ids = [id_elem.text for id_elem in root.findall('.//IdList/Id')]

                # Exit if no more IDs are found
                if not ids:
                    break

                # Add IDs to the list and update offset
                self.pmids.extend(ids)
                retstart += retmax

                # Break if fewer IDs were returned than requested (end of results)
                if len(ids) < retmax:
                    break

            except Exception:
                logging.error("Error fetching PMIDs", exc_info=True)
                break

        # Log the total number of PMIDs retrieved for further processing
        logging.info(f"Found {len(self.pmids)} paper(s) for initial screening")


    def fetch_paper_details(self):
        """
        Fetch detailed information for batches of PMIDs using the EFetch API.
        Stops fetching once the number of valid results meets the maximum required.
        """
        if not self.pmids:
            logging.warning("No PMIDs to fetch")  # Warn if there are no IDs to process
            return

        batch_size = 100  # Number of PMIDs to fetch in each batch

        # Process PMIDs in batches
        for i in range(0, len(self.pmids), batch_size):
            batch_pmids = self.pmids[i:i + batch_size]  # Slice out a batch of PMIDs

            # Fetch and parse paper details for this batch
            self._fetch_batch_details(batch_pmids)

            time.sleep(0.1)  # Short pause to respect API rate limits

            # Stop early if we've gathered enough valid results
            if len(self.papers_data) >= self.max_results:
                break


    def _fetch_batch_details(self, pmids):
        """
        Fetch and parse article details for a batch of PMIDs.

        Parameters:
        pmids (list): List of PubMed IDs to fetch data for.
        """
        # Define request parameters for the EFetch API
        params = {
            'db': 'pubmed',                            # Target the PubMed database
            'id': ','.join(pmids),                     # Comma-separated list of PMIDs
            'retmode': 'xml',                          # Request XML format
            'rettype': 'abstract',                     # Request abstract-level details
            'api_key': self.api_key                    # API key for authentication
        }

        try:
            # Send the GET request to fetch article details
            response = self.session.get(f"{self.BASE_URL}efetch.fcgi", params=params)
            response.raise_for_status()  # Raise an exception for HTTP errors

            # Parse the XML response content
            root = ET.fromstring(response.content)

            # Iterate through each article in the response
            for article in root.findall('.//PubmedArticle'):
                # Extract structured data for the article
                paper_data = self._extract_paper_data(article)

                # If the article passes all filters, store it
                if paper_data:
                    self.papers_data.append(paper_data)

                    # Stop if we've collected the maximum required results
                    if len(self.papers_data) >= self.max_results:
                        break

        except Exception:
            logging.error("Error fetching paper details", exc_info=True)  # Log errors with stack trace


    def _extract_paper_data(self, article):
        """
        Extract relevant metadata from an article XML node.

        Parameters:
        article (Element): XML element for a single article.

        Returns:
        dict: Dictionary with extracted paper information, or None if not company-authored.
        """
        try:
            # Extract PubMed ID
            pmid = article.findtext('.//PMID') or "Unknown"

            # Extract article title
            title = article.findtext('.//ArticleTitle') or "No title"

            # Extract publication date (delegated to helper method)
            pub_date = self._extract_publication_date(article)

            # Extract authors and their affiliations (returns a list of dicts)
            authors_info = self._extract_authors_and_affiliations(article)

            # Identify authors with commercial/company affiliations
            company_authors = self._filter_company_authors(authors_info)

            # If no company authors are found, skip this article
            if not company_authors:
                return None

            # Extract corresponding author's email (if available)
            corresponding_email = self._extract_corresponding_email(article)

            # Extract company-related affiliations for those authors
            company_affiliations = self._extract_company_affiliations(authors_info)

            # Return structured data for valid articles
            return {
                'PubmedID': pmid,
                'Title': title,
                'Publication Date': pub_date,
                'Non-academic Author(s)': '; '.join(company_authors),
                'Company Affiliation(s)': '; '.join(company_affiliations),
                'Corresponding Author Email': corresponding_email
            }

        except Exception:
            # Log any exception during data extraction
            logging.error("Error extracting data from article", exc_info=True)
            return None


    def _extract_publication_date(self, article):
        """
        Extract publication date from article XML.

        Parameters:
        article (Element): XML element for an article.

        Returns:
        str: Formatted date string or "Unknown".
        """
        pub_date = article.find('.//PubDate')  # Look for publication date node
        if pub_date is not None:
            # Extract year, month, and day if available
            year = pub_date.findtext('Year')
            month = pub_date.findtext('Month')
            day = pub_date.findtext('Day')

            # Join available parts into a date string (e.g., "2023-May-15")
            return '-'.join(filter(None, [year, month, day])) or "Unknown"
        
        return "Unknown"  # Return fallback if date is missing


    def _extract_authors_and_affiliations(self, article):
        """
        Extract authors and their affiliations from article XML.

        Parameters:
        article (Element): XML element for an article.

        Returns:
        list: List of dictionaries containing author names and their affiliations.
        """
        authors_info = []

        # Iterate over each author listed in the article
        for author in article.findall('.//AuthorList/Author'):
            # Extract last and first name (may be missing)
            last = author.findtext('LastName')
            fore = author.findtext('ForeName')
            
            # Construct full name or fallback to last name / "Unknown"
            name = f"{fore} {last}" if fore and last else last or "Unknown"

            # Extract all affiliation strings for this author
            affiliations = [
                aff_info.findtext('Affiliation')
                for aff_info in author.findall('AffiliationInfo')
                if aff_info.findtext('Affiliation')
            ]

            # Store the structured author info
            authors_info.append({'name': name, 'affiliations': affiliations})

        return authors_info
    

    def _is_company_affiliation(self, affiliation):
        """
        Determine if an affiliation string corresponds to a company.

        Parameters:
        affiliation (str): The affiliation string.

        Returns:
        bool: True if the affiliation is from a company, False if academic or unknown.
        """
        aff_lower = affiliation.lower()  # Normalize text for case-insensitive comparison

        # Filter out affiliations that match known academic keywords
        if any(exclusion in aff_lower for exclusion in self.ACADEMIC_EXCLUSIONS):
            return False

        # Check for presence of known company names (e.g., Pfizer, Novartis)
        if any(company in aff_lower for company in self.KNOWN_COMPANIES):
            return True

        # Check for legal/business entity terms (e.g., Inc, Ltd, GmbH)
        if any(entity in aff_lower for entity in self.LEGAL_ENTITIES):
            return True

        # Check for generic industry-related keywords (e.g., biotech, therapeutics)
        if any(keyword in aff_lower for keyword in self.COMPANY_KEYWORDS):
            return True

        return False  # If none of the above match, assume it's not a company
        

    def _filter_company_authors(self, authors_info):
        """
        Identify authors who are affiliated with companies.

        Parameters:
        authors_info (list): List of author metadata.

        Returns:
        list: Unique names of authors with company affiliations.
        """
        company_authors = []

        # Iterate through each author and check if any of their affiliations are company-related
        for author in authors_info:
            # If at least one affiliation is identified as a company, include the author
            if any(self._is_company_affiliation(aff) for aff in author['affiliations']):
                company_authors.append(author['name'])

        # Remove duplicates using set and return a list of unique author names
        return list(set(company_authors))


    def _extract_company_affiliations(self, authors_info):
        """
        Collect all unique company affiliations from authors.

        Parameters:
        authors_info (list): List of author metadata.

        Returns:
        list: Unique company affiliation strings.
        """
        company_affiliations = []

        # Go through each author's list of affiliations
        for author in authors_info:
            # Filter affiliations that qualify as company-based
            company_affiliations.extend(
                aff for aff in author['affiliations'] if self._is_company_affiliation(aff)
            )

        # Deduplicate the list and return
        return list(set(company_affiliations))


    def _extract_corresponding_email(self, article):
        """
        Extract the first email address found in the abstract text.

        Parameters:
        article (Element): XML element for an article.

        Returns:
        str: Email address or 'Not available'.
        """
        # Search within all AbstractText elements for an email pattern
        text_fields = article.findall('.//AbstractText')

        for elem in text_fields:
            if elem.text:
                # Use regex to locate the first email-like string
                match = re.search(r'[\w\.-]+@[\w\.-]+', elem.text)
                if match:
                    return match.group(0)  # Return the matched email

        return "Not available"  # If no email is found in any abstract section


    def save_to_csv(self, filename="pubmed_results.csv"):
        """
        Save the filtered paper metadata to a CSV file.

        Parameters:
        filename (str): Path to the CSV file.
        """
        # Check if there's any data to write
        if not self.papers_data:
            logging.warning("No data to save")
            return

        # Define the expected column headers
        fieldnames = [
            'PubmedID', 'Title', 'Publication Date',
            'Non-academic Author(s)', 'Company Affiliation(s)',
            'Corresponding Author Email'
        ]

        try:
            # Open the target CSV file for writing
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()  # Write column headers
                writer.writerows(self.papers_data)  # Write all data rows

            logging.info(f"Results saved to {filename}")
            logging.info(f"Total papers with company-affiliated authors: {len(self.papers_data)}")

        except Exception:
            logging.error("Error saving CSV", exc_info=True)


    def print_label_format(self):
        """
        Print paper data in a labeled format to the console for readability.
        """
        # Warn if there's no data to display
        if not self.papers_data:
            logging.warning("No data to print")
            return

        # Print each paper's information in a human-readable format
        for idx, paper in enumerate(self.papers_data, 1):
            print("\n\n")  # Add extra spacing for clarity
            print(f"\n--- Paper {idx} ---")
            print(f"PubmedID: {paper['PubmedID']}")
            print(f"Title: {paper['Title']}")
            print(f"Publication Date: {paper['Publication Date']}")
            print(f"Non-academic Author(s): {paper['Non-academic Author(s)']}")
            print(f"Company Affiliation(s): {paper['Company Affiliation(s)']}")
            print(f"Corresponding Author Email: {paper['Corresponding Author Email']}")
            print("-" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Search PubMed for papers with non-academic authors and extract relevant details."
    )

    parser.add_argument("query", nargs="?", help="Search query for PubMed.")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug logging.")
    parser.add_argument("-f", "--file", type=str, help="Output filename (CSV).")
    parser.add_argument("-m", "--max", type=int, default=20, help="Max number of results (default 20)")

    args = parser.parse_args()

    # Set logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.debug("Debug mode is enabled")

    # Check for query
    if not args.query:
        logging.error("No query provided. Use -h for help.")
        sys.exit(1)

    API_KEY = "6f26a8573bb6248f570994bba6d54c92b708"
    query = args.query
    max_results = args.max if args.max > 0 else 20

    fetcher = PubMedFetcher(query, API_KEY, max_results)
    fetcher.fetch_pmids()
    fetcher.fetch_paper_details()

    if args.file:
        fetcher.save_to_csv(filename=args.file)
    else:
        fetcher.print_label_format()


if __name__ == "__main__":
    # if len(sys.argv) > 1:
        main()