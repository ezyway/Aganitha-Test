import requests

class PubMedFetcher:
    def __init__(self, api_key, max_results=100):
        self.api_key = api_key
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
        
def main():
    API_key = "6f26a8573bb6248f570994bba6d54c92b708"
    query = input("Enter PubMed search keywords: ")
    try:
        max_results = int(input("How many results to fetch? (max 100): ") or 100)
        if max_results > 100:
            max_results = 100
    except ValueError:
        max_results = 100

    fetcher = PubMedFetcher(query, API_key, max_results)
    

if __name__ == "__main__":
    main()