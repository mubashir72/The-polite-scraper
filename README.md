# The Polite Scraper 🕷️

A small, polite scraping pipeline that downloads the first three catalogue pages of [Books to Scrape](https://books.toscrape.com), visits all 60 book pages, turns messy HTML into clean, validated JSON records, survives broken pages without crashing, and ends every run with an honest report.

---

## Target Classification

| Field | Value |
|---|---|
| **Target Site** | [Books to Scrape](https://books.toscrape.com) |
| **Why** | The site explicitly states it is a sandbox designed for people to practise web scraping. |
| **Scope** | First 3 catalogue pages only (60 books). |
| **Data collected** | Title, price, availability, rating, description, product URL. |
| **robots.txt** | Checked `https://books.toscrape.com/robots.txt` — returned 404 (no robots file found). |

> I will not reuse this code on another site without checking its rules and terms first.

---

## Quick Start

**Lane:** Python 3.10+

### Install dependencies

```bash
pip install beautifulsoup4 pydantic
```

### Run the scraper

```bash
python src/main.py
```

Output files appear in `output/`:
- `books.json` — 60 validated book records
- `errors.json` — any records that failed validation
- `run-report.json` — run statistics

---

## Record Schema (Pydantic)

```python
class BookRecord(BaseModel):
    title: str                        # Book title
    product_url: str                  # Canonical URL (must start with https://)
    price_text: str                   # Raw price string, e.g. "£51.77"
    price_gbp: float                  # Cleaned price as a number, e.g. 51.77
    availability_text: str            # e.g. "In stock (22 available)"
    rating_text: str                  # e.g. "Three"
    description: Optional[str]        # May be null if the book has no description
    source_page: str                  # Which catalogue page linked to this book
    fetched_at: str                   # ISO 8601 timestamp of when the page was fetched
```

---

## Politeness Rules

| Rule | Implementation |
|---|---|
| **User-Agent** | `FlyRankInternshipA9/1.0 (+https://github.com/mubashir72/The-polite-scraper)` — identifies who we are so a site owner can find us in their logs. |
| **Delay** | At least 0.5 seconds between real network requests. Cached pages need no delay. |
| **Timeout** | Every request gives up after 5 seconds — we never wait forever. |
| **Caching** | HTML is saved locally on first fetch. All subsequent runs read from cache, so the site feels the scraper only once. |
| **Retry** | Retry once on 5xx / timeout. Never retry 404 (page doesn't exist) or 403 (site said no). |

---

## Sample Run Report

```json
{
  "start_time": "2026-10-03T09:12:08Z",
  "end_time": "2026-10-03T09:12:08Z",
  "duration_seconds": 0.51,
  "pages_fetched": 0,
  "cache_hits": 63,
  "valid_records": 60,
  "invalid_records": 0,
  "failed_pages": 0,
  "failed_urls": []
}
```

> This cached run completed in ~0.5 seconds. The first run (fetching all 63 pages from the network) takes about 35 seconds due to polite delays.

---

## Why No Browser?

This assignment needed no browser because the data (titles, prices, availability) is already present in the HTML the server sends in response to a simple HTTP GET. A headless browser would only add startup cost, memory overhead, and complexity — with zero benefit for static content.

---

## Limitations

- **Static content only.** This scraper cannot handle JavaScript-rendered pages. If the site switched to client-side rendering, we would need a headless browser like Playwright.

---

## Ethics Note

Always prefer an official API when one exists — it is the door the site built for you. Never bypass logins, paywalls, rate limits, or access blocks. Collect only the data you actually need, and only from sites that permit it. A scraper is a guest; behave like one.

---

## Git Log

```
87be9cd Stage 5: survive failures, report the run
9163fed Stage 4: validate normalized records
5cf2f4d Stage 3: extract book details
5186c5b Stage 2: discover three catalogue pages
eff42df Stage 2: discover three catalogue pages
51b349b Stage 0: classify scraping target
f23dbb0 first commit
```
