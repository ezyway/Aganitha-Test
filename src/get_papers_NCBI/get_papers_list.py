import requests
import xml.etree.ElementTree as ET
import argparse
import csv
import re
import time
import logging
import sys
from urllib.parse import quote_plus

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class PubMedFetcher:
    """
    A class to fetch and filter PubMed papers based on author affiliations, specifically targeting commercial companies.
    """

    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

    COMPANY_KEYWORDS = [
        'biotech', 'biotechnology', 'therapeutics', 'sciences', 'solutions', 
        'technologies', 'biosciences', 'biopharma', 'biopharmaceuticals'
    ]

    LEGAL_ENTITIES = [
        'corp', 'corporation', 'company', 'inc', 'ltd', 'llc', 'llp',
        'gmbh', 'ag', 'sa', 'bv', 'nv', 'srl', 'spa', 'plc', 'pty',
        'co.', 'co ', ' co', 'limited', 'enterprises', 'holdings'
    ]

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
        self.api_key = api_key
        self.query = query
        self.max_results = max_results
        self.pmids = []
        self.papers_data = []
        self.session = requests.Session()

    def fetch_pmids(self):
        """
        Retrieve PubMed IDs (PMIDs) matching the query using the esearch API.
        Fetch extra PMIDs to account for filtering non-company affiliations later.
        """
        search_query = self.query
        retmax = 100
        retstart = 0

        while len(self.pmids) < self.max_results * 5:
            params = {
                'db': 'pubmed',
                'term': search_query,
                'retmax': retmax,
                'retstart': retstart,
                'retmode': 'xml',
                'api_key': self.api_key
            }
            try:
                response = self.session.get(f"{self.BASE_URL}esearch.fcgi", params=params)
                response.raise_for_status()
                root = ET.fromstring(response.content)
                ids = [id_elem.text for id_elem in root.findall('.//IdList/Id')]

                if not ids:
                    break

                self.pmids.extend(ids)
                retstart += retmax
                if len(ids) < retmax:
                    break

            except Exception:
                logging.error("Error fetching PMIDs", exc_info=True)
                break

        logging.info(f"Found {len(self.pmids)} paper(s) for initial screening")

    def fetch_paper_details(self):
        """
        Fetch detailed information for batches of PMIDs using the efetch API.
        Stops fetching once the number of valid results meets the maximum required.
        """
        if not self.pmids:
            logging.warning("No PMIDs to fetch")
            return

        batch_size = 100
        for i in range(0, len(self.pmids), batch_size):
            batch_pmids = self.pmids[i:i + batch_size]
            self._fetch_batch_details(batch_pmids)
            time.sleep(0.1)
            if len(self.papers_data) >= self.max_results:
                break

    def _fetch_batch_details(self, pmids):
        """
        Fetch and parse article details for a batch of PMIDs.

        Parameters:
        pmids (list): List of PubMed IDs to fetch data for.
        """
        params = {
            'db': 'pubmed',
            'id': ','.join(pmids),
            'retmode': 'xml',
            'rettype': 'abstract',
            'api_key': self.api_key
        }

        try:
            response = self.session.get(f"{self.BASE_URL}efetch.fcgi", params=params)
            response.raise_for_status()
            root = ET.fromstring(response.content)

            for article in root.findall('.//PubmedArticle'):
                paper_data = self._extract_paper_data(article)
                if paper_data:
                    self.papers_data.append(paper_data)
                    if len(self.papers_data) >= self.max_results:
                        break

        except Exception:
            logging.error("Error fetching paper details", exc_info=True)

    def _extract_paper_data(self, article):
        """
        Extract relevant metadata from an article XML node.

        Parameters:
        article (Element): XML element for a single article.

        Returns:
        dict: Dictionary with extracted paper information, or None if not company-authored.
        """
        try:
            pmid = article.findtext('.//PMID') or "Unknown"
            title = article.findtext('.//ArticleTitle') or "No title"
            pub_date = self._extract_publication_date(article)
            authors_info = self._extract_authors_and_affiliations(article)
            company_authors = self._filter_company_authors(authors_info)

            if not company_authors:
                return None

            corresponding_email = self._extract_corresponding_email(article)
            company_affiliations = self._extract_company_affiliations(authors_info)

            return {
                'PubmedID': pmid,
                'Title': title,
                'Publication Date': pub_date,
                'Non-academic Author(s)': '; '.join(company_authors),
                'Company Affiliation(s)': '; '.join(company_affiliations),
                'Corresponding Author Email': corresponding_email
            }

        except Exception:
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
        pub_date = article.find('.//PubDate')
        if pub_date is not None:
            year = pub_date.findtext('Year')
            month = pub_date.findtext('Month')
            day = pub_date.findtext('Day')
            return '-'.join(filter(None, [year, month, day])) or "Unknown"
        return "Unknown"

    def _extract_authors_and_affiliations(self, article):
        """
        Extract authors and their affiliations from article XML.

        Parameters:
        article (Element): XML element for an article.

        Returns:
        list: List of dictionaries containing author names and their affiliations.
        """
        authors_info = []
        for author in article.findall('.//AuthorList/Author'):
            last = author.findtext('LastName')
            fore = author.findtext('ForeName')
            name = f"{fore} {last}" if fore and last else last or "Unknown"

            affiliations = [aff_info.findtext('Affiliation')
                            for aff_info in author.findall('AffiliationInfo') if aff_info.findtext('Affiliation')]

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
        aff_lower = affiliation.lower()

        if any(exclusion in aff_lower for exclusion in self.ACADEMIC_EXCLUSIONS):
            return False

        if any(company in aff_lower for company in self.KNOWN_COMPANIES):
            return True

        if any(entity in aff_lower for entity in self.LEGAL_ENTITIES):
            return True

        if any(keyword in aff_lower for keyword in self.COMPANY_KEYWORDS):
            return True

        return False

    def _filter_company_authors(self, authors_info):
        """
        Identify authors who are affiliated with companies.

        Parameters:
        authors_info (list): List of author metadata.

        Returns:
        list: Unique names of authors with company affiliations.
        """
        company_authors = []
        for author in authors_info:
            if any(self._is_company_affiliation(aff) for aff in author['affiliations']):
                company_authors.append(author['name'])

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
        for author in authors_info:
            company_affiliations.extend(
                aff for aff in author['affiliations'] if self._is_company_affiliation(aff)
            )

        return list(set(company_affiliations))

    def _extract_corresponding_email(self, article):
        """
        Extract the first email address found in the abstract text.

        Parameters:
        article (Element): XML element for an article.

        Returns:
        str: Email address or 'Not available'.
        """
        text_fields = article.findall('.//AbstractText')
        for elem in text_fields:
            if elem.text:
                match = re.search(r'[\w\.-]+@[\w\.-]+', elem.text)
                if match:
                    return match.group(0)
        return "Not available"

    def save_to_csv(self, filename="pubmed_results.csv"):
        """
        Save the filtered paper metadata to a CSV file.

        Parameters:
        filename (str): Path to the CSV file.
        """
        if not self.papers_data:
            logging.warning("No data to save")
            return

        fieldnames = [
            'PubmedID', 'Title', 'Publication Date',
            'Non-academic Author(s)', 'Company Affiliation(s)',
            'Corresponding Author Email'
        ]

        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.papers_data)

            logging.info(f"Results saved to {filename}")
            logging.info(f"Total papers with company-affiliated authors: {len(self.papers_data)}")
        except Exception:
            logging.error("Error saving CSV", exc_info=True)

    def print_label_format(self):
        """
        Print paper data in a labeled format to the console for readability.
        """
        if not self.papers_data:
            logging.warning("No data to print")
            return

        for idx, paper in enumerate(self.papers_data, 1):
            print("\n\n")
            print(f"\n--- Paper {idx} ---")
            print(f"PubmedID: {paper['PubmedID']}")
            print(f"Title: {paper['Title']}")
            print(f"Publication Date: {paper['Publication Date']}")
            print(f"Non-academic Author(s): {paper['Non-academic Author(s)']}")
            print(f"Company Affiliation(s): {paper['Company Affiliation(s)']}")
            print(f"Corresponding Author Email: {paper['Corresponding Author Email']}")
            print("-" * 60)



# def main():
#     query = input("Enter PubMed search keywords: ").strip()
#     try:
#         max_results = int(input("How many results to fetch? (default 20): ") or 20)
#         if max_results < 1:
#             max_results = 20
#     except ValueError:
#         max_results = 20

#     API_KEY = "6f26a8573bb6248f570994bba6d54c92b708"
#     fetcher = PubMedFetcher(query, API_KEY, max_results)
#     fetcher.fetch_pmids()
#     fetcher.fetch_paper_details()
#     fetcher.print_label_format()

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