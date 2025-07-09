import requests
import xml.etree.ElementTree as ET
import csv
import re
import time
import logging
from urllib.parse import quote_plus

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class PubMedFetcher:
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    
    COMPANY_KEYWORDS = [
        'pharmaceutical', 'pharma', 'biotech', 'biotechnology',
        'company', 'corp', 'corporation', 'inc', 'ltd', 'llc',
        'therapeutics', 'sciences', 'solutions', 'technologies',
        'pfizer', 'moderna', 'johnson', 'merck', 'roche', 'novartis',
        'sanofi', 'astrazeneca', 'gsk', 'abbvie', 'biogen', 'amgen',
        'gilead', 'vertex', 'illumina'
    ]
    
    def __init__(self, query, api_key, max_results=100):
        self.api_key = api_key
        self.query = query
        self.max_results = max_results
        self.pmids = []
        self.papers_data = []
        self.session = requests.Session()
    
    def fetch_pmids(self):
        """Search PubMed and get PMIDs (with pagination support)"""
        search_query = f"{self.query} AND (pharmaceutical[Affiliation] OR biotech[Affiliation] OR pharma[Affiliation])"
        retmax = 100
        retstart = 0

        while len(self.pmids) < self.max_results:
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
                    break  # No more pages

            except requests.exceptions.RequestException as e:
                logging.error("Error fetching PMIDs", exc_info=True)
                break
            except ET.ParseError as e:
                logging.error("Error parsing XML for PMIDs", exc_info=True)
                break

        self.pmids = self.pmids[:self.max_results]
        logging.info(f"Found {len(self.pmids)} paper(s)")

    def fetch_paper_details(self):
        if not self.pmids:
            logging.warning("No PMIDs to fetch")
            return

        batch_size = 100
        for i in range(0, len(self.pmids), batch_size):
            batch_pmids = self.pmids[i:i + batch_size]
            self._fetch_batch_details(batch_pmids)
            time.sleep(0.1)  # Rate limiting

    def _fetch_batch_details(self, pmids):
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

        except requests.exceptions.RequestException as e:
            logging.error("Error fetching paper details", exc_info=True)
        except ET.ParseError as e:
            logging.error("Error parsing XML for paper details", exc_info=True)

    def _extract_paper_data(self, article):
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
        pub_date = article.find('.//PubDate')
        if pub_date is not None:
            year = pub_date.findtext('Year')
            month = pub_date.findtext('Month')
            day = pub_date.findtext('Day')

            return '-'.join(filter(None, [year, month, day])) or "Unknown"
        return "Unknown"

    def _extract_authors_and_affiliations(self, article):
        authors_info = []
        for author in article.findall('.//AuthorList/Author'):
            last = author.findtext('LastName')
            fore = author.findtext('ForeName')
            name = f"{fore} {last}" if fore and last else last or "Unknown"

            affiliations = []
            for aff_info in author.findall('AffiliationInfo'):
                aff = aff_info.findtext('Affiliation')
                if aff:
                    affiliations.append(aff)

            authors_info.append({'name': name, 'affiliations': affiliations})
        return authors_info

    def _filter_company_authors(self, authors_info):
        return list({
            author['name']
            for author in authors_info
            for aff in author['affiliations']
            if any(keyword in aff.lower() for keyword in self.COMPANY_KEYWORDS)
        })

    def _extract_company_affiliations(self, authors_info):
        return list({
            aff
            for author in authors_info
            for aff in author['affiliations']
            if any(keyword in aff.lower() for keyword in self.COMPANY_KEYWORDS)
        })

    def _extract_corresponding_email(self, article):
        # Optional: use regex to try extracting email from abstract or affiliations
        text_fields = article.findall('.//AbstractText')
        for elem in text_fields:
            if elem.text:
                match = re.search(r'[\w\.-]+@[\w\.-]+', elem.text)
                if match:
                    return match.group(0)
        return "Not available"

    def save_to_csv(self, filename="pubmed_results.csv"):
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

    def run(self):
        logging.info("Starting PubMed search...")
        self.fetch_pmids()
        if self.pmids:
            logging.info("Fetching paper details...")
            self.fetch_paper_details()
            logging.info("Saving results to CSV...")
            self.save_to_csv()
        else:
            logging.info("No papers found matching criteria")

def main():
    API_KEY = "6f26a8573bb6248f570994bba6d54c92b708"
    query = input("Enter PubMed search keywords: ").strip()
    try:
        max_results = int(input("How many results to fetch? (default 100): ") or 100)
        if max_results < 1:
            logging.warning("Number too low, defaulting to 100")
            max_results = 100
    except ValueError:
        max_results = 100

    fetcher = PubMedFetcher(query, API_KEY, max_results)
    fetcher.run()

if __name__ == "__main__":
    main()
