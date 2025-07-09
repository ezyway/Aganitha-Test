# NCBI PubMed E-utilities API Guide

## Overview
This guide covers the essential NCBI E-utilities for searching and retrieving PubMed research papers with author affiliation filtering.

## Required Parameters
- **API Key**: Include in all requests as `api_key=YOUR_KEY`
- **Rate Limits**: 10 requests/second with API key (3 without)
- **Tool/Email**: Register with NCBI if blocked

## Base URL
```
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/
```

## Essential E-utilities for PubMed

### 1. ESearch - Find Papers by Keywords
**Endpoint**: `esearch.fcgi`

**Purpose**: Search PubMed with keywords and get PMIDs (PubMed IDs)

**Key Parameters**:
- `db=pubmed` (required)
- `term=` (search query)
- `retmax=` (max results, default 20, max 100 for this use case)
- `retstart=` (pagination offset)
- `usehistory=y` (store results on server for batch processing)

**Example**:
```
esearch.fcgi?db=pubmed&term=cancer+drug&retmax=50&api_key=YOUR_KEY
```

### 2. EFetch - Get Full Paper Details
**Endpoint**: `efetch.fcgi`

**Purpose**: Retrieve detailed information using PMIDs from ESearch

**Key Parameters**:
- `db=pubmed` (required)
- `id=` (comma-separated PMIDs)
- `retmode=xml` (recommended for parsing)
- `rettype=abstract` (or `medline`)

**Example**:
```
efetch.fcgi?db=pubmed&id=12345,67890&retmode=xml&api_key=YOUR_KEY
```

### 3. ESummary - Get Paper Summaries
**Endpoint**: `esummary.fcgi`

**Purpose**: Get brief summaries (faster than EFetch for basic info)

**Key Parameters**:
- `db=pubmed` (required)
- `id=` (comma-separated PMIDs)
- `retmode=json` (easier to parse than XML)

**Example**:
```
esummary.fcgi?db=pubmed&id=12345,67890&retmode=json&api_key=YOUR_KEY
```

## Search Query Construction

### Basic Search Patterns
- Simple keywords: `cancer+drug`
- Phrase search: `"stem+cell"`
- Field-specific: `"Pfizer"[Affiliation]`
- Boolean operators: `CRISPR+AND+therapy`

### Author Affiliation Filtering
- Pharma/biotech companies: `"Pfizer"[Affiliation] OR "Moderna"[Affiliation]`
- Generic terms: `"pharmaceutical"[Affiliation] OR "biotech"[Affiliation]`
- Combined: `diabetes+AND+("Novo Nordisk"[Affiliation] OR "Sanofi"[Affiliation])`

## Typical Workflow

1. **Search**: Use `ESearch` with keywords + affiliation filters
2. **Retrieve**: Use `EFetch` or `ESummary` with returned PMIDs
3. **Parse**: Extract title, authors, journal, date, doi, affiliation
4. **Filter**: Further filter by author affiliations in results
5. **Export**: Save to CSV

## Response Data Structure

### ESearch Response (XML)
```xml
<eSearchResult>
  <Count>25</Count>
  <RetMax>20</RetMax>
  <IdList>
    <Id>12345</Id>
    <Id>67890</Id>
  </IdList>
</eSearchResult>
```

### EFetch Response (Key Fields)
- `PubmedArticle/MedlineCitation/Article/ArticleTitle`
- `PubmedArticle/MedlineCitation/Article/AuthorList/Author`
- `PubmedArticle/MedlineCitation/Article/Journal/Title`
- `PubmedArticle/MedlineCitation/Article/AuthorList/Author/AffiliationInfo`
- `PubmedArticle/MedlineCitation/Article/ELocationID` (DOI)

## Error Handling
- Rate limit error: `{"error":"API rate limit exceeded","count":"11"}`
- Invalid query: Check for empty IdList in response
- Connection timeout: Implement retry logic

## Best Practices
- Use `usehistory=y` for batch processing >100 records
- Combine multiple company names in single query
- Add retry logic with exponential backoff
- Cache results to avoid repeated API calls
- Use `retmax=100` for maximum efficiency</tml:parameter>
</invoke>



API KEY - 6f26a8573bb6248f570994bba6d54c92b708