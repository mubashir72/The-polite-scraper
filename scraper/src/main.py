import os
import re
import time
import json
import datetime
import urllib.request
from urllib.error import URLError, HTTPError
from urllib.parse import urljoin
from typing import Optional
from bs4 import BeautifulSoup
from pydantic import BaseModel, field_validator

# ── Pydantic schema ─────────────────────────────────────────────
class BookRecord(BaseModel):
    title: str
    product_url: str
    price_text: str
    price_gbp: float
    availability_text: str
    rating_text: str
    description: Optional[str] = None
    source_page: str
    fetched_at: str

    @field_validator('product_url', 'source_page')
    @classmethod
    def must_be_https(cls, v: str) -> str:
        if not v.startswith('https://'):
            raise ValueError(f'URL must start with https://, got: {v}')
        return v

    @field_validator('price_gbp')
    @classmethod
    def price_must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError(f'price_gbp must be positive, got: {v}')
        return v

# ── Run stats tracker ───────────────────────────────────────────
class RunStats:
    def __init__(self):
        self.start_time = datetime.datetime.now(datetime.timezone.utc)
        self.pages_fetched = 0
        self.cache_hits = 0
        self.valid_records = 0
        self.invalid_records = 0
        self.failed_pages = 0
        self.failed_urls = []

    def to_dict(self):
        end_time = datetime.datetime.now(datetime.timezone.utc)
        duration = (end_time - self.start_time).total_seconds()
        return {
            "start_time": self.start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end_time": end_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "duration_seconds": round(duration, 2),
            "pages_fetched": self.pages_fetched,
            "cache_hits": self.cache_hits,
            "valid_records": self.valid_records,
            "invalid_records": self.invalid_records,
            "failed_pages": self.failed_pages,
            "failed_urls": self.failed_urls,
        }

# ── Helpers ──────────────────────────────────────────────────────
USER_AGENT = 'FlyRankInternshipA9/1.0 (+https://github.com/mubashir72/The-polite-scraper)'

def fetch_and_cache_page(url, cache_path, stats: RunStats):
    """Fetch a page with caching, retry on 5xx/timeout, skip on 404/403."""
    if os.path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8') as f:
            html = f.read()
        stats.cache_hits += 1
        return html

    max_retries = 2
    for attempt in range(max_retries):
        print(f"FETCH (attempt {attempt + 1}): {url}")
        req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})

        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                status = response.getcode()
                if status != 200:
                    print(f"  Non-200 status: {status}")
                    return None

                html_bytes = response.read()
                html = html_bytes.decode('utf-8')

                os.makedirs(os.path.dirname(cache_path), exist_ok=True)
                with open(cache_path, 'w', encoding='utf-8') as f:
                    f.write(html)

                stats.pages_fetched += 1
                return html

        except HTTPError as e:
            code = e.code
            print(f"  HTTP {code}: {e.reason}")
            # Do NOT retry 403 or 404
            if code in (403, 404):
                return None
            # Retry on 5xx
            if code >= 500 and attempt < max_retries - 1:
                print("  Retrying after 1s...")
                time.sleep(1)
                continue
            return None

        except (URLError, TimeoutError, OSError) as e:
            print(f"  Network error: {e}")
            if attempt < max_retries - 1:
                print("  Retrying after 1s...")
                time.sleep(1)
                continue
            return None

        except Exception as e:
            print(f"  Unexpected error: {e}")
            return None

    return None


def extract_catalogue_page(html, base_url):
    soup = BeautifulSoup(html, 'html.parser')
    books = []

    for h3 in soup.select('article.product_pod h3 a'):
        href = h3.get('href')
        if href:
            absolute_url = urljoin(base_url, href)
            books.append({
                'url': absolute_url,
                'source_page': base_url
            })

    next_link = None
    next_li = soup.select_one('li.next a')
    if next_li:
        href = next_li.get('href')
        next_link = urljoin(base_url, href)

    return books, next_link


def extract_book_details(html, product_url, source_page, fetched_at):
    soup = BeautifulSoup(html, 'html.parser')

    article = soup.find('article', class_='product_page')
    if not article:
        return None

    title_tag = article.find('h1')
    title = title_tag.text if title_tag else None

    price_tag = article.find('p', class_='price_color')
    price_text = price_tag.text if price_tag else None

    availability_tag = article.find('p', class_='instock availability')
    availability_text = availability_tag.text.strip() if availability_tag else None

    rating_tag = article.find('p', class_='star-rating')
    rating_text = None
    if rating_tag:
        classes = rating_tag.get('class', [])
        for c in classes:
            if c != 'star-rating':
                rating_text = c
                break

    description = None
    desc_div = article.find('div', id='product_description')
    if desc_div:
        desc_p = desc_div.find_next_sibling('p')
        if desc_p:
            description = desc_p.text

    return {
        "title": title,
        "product_url": product_url,
        "price_text": price_text,
        "availability_text": availability_text,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": fetched_at
    }


# ── Normalization ────────────────────────────────────────────────
def normalize_price(price_text: str) -> Optional[float]:
    """Turn '£51.77' or 'Â£51.77' into 51.77."""
    if not price_text:
        return None
    match = re.search(r'[\d]+\.[\d]{2}', price_text)
    if match:
        return float(match.group())
    return None


def normalize_record(raw: dict) -> dict:
    """Add cleaned fields alongside the raw ones."""
    cleaned = dict(raw)
    cleaned['price_gbp'] = normalize_price(raw.get('price_text', ''))
    return cleaned


# ── Main pipeline ────────────────────────────────────────────────
def main():
    stats = RunStats()

    start_url = "https://books.toscrape.com/catalogue/page-1.html"
    current_url = start_url

    catalogue_pages = 0
    all_books = []
    max_pages = 3

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # 1. Traverse catalogue pages
    while current_url and catalogue_pages < max_pages:
        catalogue_pages += 1
        page_name = os.path.basename(current_url)
        if not page_name.endswith('.html'):
            page_name += '.html'

        cache_path = os.path.join(base_dir, "cache", page_name)

        is_cached = os.path.exists(cache_path)
        if not is_cached and catalogue_pages > 1:
            time.sleep(0.5)

        html = fetch_and_cache_page(current_url, cache_path, stats)
        if not html:
            break

        books, next_link = extract_catalogue_page(html, current_url)
        all_books.extend(books)

        current_url = next_link

    # Deduplicate by URL
    unique_books = {}
    for b in all_books:
        if b['url'] not in unique_books:
            unique_books[b['url']] = b

    # Inject one fake URL to prove resilience (test only)
    fake_url = "https://books.toscrape.com/catalogue/this-book-does-not-exist_0000/index.html"
    unique_books[fake_url] = {
        'url': fake_url,
        'source_page': 'https://books.toscrape.com/catalogue/page-1.html'
    }

    # 2. Extract raw records from each book page (per-page error handling)
    raw_records = []
    for url, info in unique_books.items():
        try:
            parts = url.split('/')
            book_id = parts[-2] if len(parts) > 1 else "unknown"
            cache_path = os.path.join(base_dir, "cache", f"book_{book_id}.html")

            is_cached = os.path.exists(cache_path)
            if not is_cached:
                time.sleep(0.5)

            html = fetch_and_cache_page(url, cache_path, stats)
            if not html:
                stats.failed_pages += 1
                stats.failed_urls.append(url)
                print(f"  SKIPPED (no HTML): {url}")
                continue

            if is_cached:
                mtime = os.path.getmtime(cache_path)
                fetched_at = datetime.datetime.fromtimestamp(mtime, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            else:
                fetched_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            record = extract_book_details(html, url, info['source_page'], fetched_at)
            if record:
                raw_records.append(record)
            else:
                stats.failed_pages += 1
                stats.failed_urls.append(url)
                print(f"  SKIPPED (parse failed): {url}")

        except Exception as e:
            stats.failed_pages += 1
            stats.failed_urls.append(url)
            print(f"  ERROR processing {url}: {e}")

    # 3. Normalize + Validate
    valid_records = []
    error_records = []

    for raw in raw_records:
        normalized = normalize_record(raw)
        try:
            book = BookRecord(**normalized)
            valid_records.append(book.model_dump())
        except Exception as e:
            error_records.append({
                "record": raw,
                "error": str(e)
            })

    # Deduplicate valid records by product_url (idempotency)
    seen_urls = set()
    deduped = []
    for rec in valid_records:
        if rec['product_url'] not in seen_urls:
            seen_urls.add(rec['product_url'])
            deduped.append(rec)
    valid_records = deduped

    stats.valid_records = len(valid_records)
    stats.invalid_records = len(error_records)

    # 4. Store
    output_dir = os.path.join(base_dir, "output")
    os.makedirs(output_dir, exist_ok=True)

    books_path = os.path.join(output_dir, "books.json")
    with open(books_path, 'w', encoding='utf-8') as f:
        json.dump(valid_records, f, indent=2, ensure_ascii=False)

    errors_path = os.path.join(output_dir, "errors.json")
    with open(errors_path, 'w', encoding='utf-8') as f:
        json.dump(error_records, f, indent=2, ensure_ascii=False)

    # 5. Write run report
    report = stats.to_dict()
    report_path = os.path.join(output_dir, "run-report.json")
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # 6. Print summary
    print(f"\n{'='*50}")
    print(f"RUN REPORT")
    print(f"{'='*50}")
    print(json.dumps(report, indent=2))
    print(f"\nbooks.json:  {stats.valid_records} records")
    print(f"errors.json: {stats.invalid_records} records")
    print(f"failed_pages: {stats.failed_pages}")


if __name__ == "__main__":
    main()
