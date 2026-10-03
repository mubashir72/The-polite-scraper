import os
import time
import json
import datetime
import urllib.request
from urllib.error import URLError, HTTPError
from urllib.parse import urljoin
from bs4 import BeautifulSoup

def fetch_and_cache_page(url, cache_path):
    if os.path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8') as f:
            html = f.read()
        return html

    print(f"FETCH: {url}")
    req = urllib.request.Request(
        url, 
        headers={'User-Agent': 'FlyRankInternshipA9/1.0 (+https://github.com/mubashir72/The-polite-scraper)'}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            status = response.getcode()
            if status != 200:
                print(f"Failed to fetch {url}. Status code: {status}")
                return None
            
            html_bytes = response.read()
            html = html_bytes.decode('utf-8')
            
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            with open(cache_path, 'w', encoding='utf-8') as f:
                f.write(html)
            
            return html
    except Exception as e:
        print(f"An error occurred while fetching {url}: {e}")
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

def main():
    start_url = "https://books.toscrape.com/catalogue/page-1.html"
    current_url = start_url
    
    catalogue_pages = 0
    all_books = []
    max_pages = 3
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 1. Traverse catalogue
    while current_url and catalogue_pages < max_pages:
        catalogue_pages += 1
        page_name = os.path.basename(current_url)
        if not page_name.endswith('.html'):
            page_name += '.html'
            
        cache_path = os.path.join(base_dir, "cache", page_name)
        
        is_cached = os.path.exists(cache_path)
        if not is_cached and catalogue_pages > 1:
            time.sleep(0.5)
            
        html = fetch_and_cache_page(current_url, cache_path)
        if not html:
            break
            
        books, next_link = extract_catalogue_page(html, current_url)
        all_books.extend(books)
        
        current_url = next_link
        
    # Deduplicate
    unique_books = {}
    for b in all_books:
        if b['url'] not in unique_books:
            unique_books[b['url']] = b
            
    # 2. Extract books
    book_records = []
    for url, info in unique_books.items():
        parts = url.split('/')
        book_id = parts[-2] if len(parts) > 1 else "unknown"
        cache_path = os.path.join(base_dir, "cache", f"book_{book_id}.html")
        
        is_cached = os.path.exists(cache_path)
        if not is_cached:
            time.sleep(0.5)
            
        html = fetch_and_cache_page(url, cache_path)
        if html:
            if is_cached:
                mtime = os.path.getmtime(cache_path)
                fetched_at = datetime.datetime.fromtimestamp(mtime, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            else:
                fetched_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                
            record = extract_book_details(html, url, info['source_page'], fetched_at)
            if record:
                book_records.append(record)
                
    # Checkpoint
    if book_records:
        print(json.dumps(book_records[0], indent=2))
        
    print(f"detail_pages={len(book_records)}")

if __name__ == "__main__":
    main()
