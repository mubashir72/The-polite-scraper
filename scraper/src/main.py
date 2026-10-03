import os
import time
import urllib.request
from urllib.error import URLError, HTTPError
from urllib.parse import urljoin
from bs4 import BeautifulSoup

def fetch_and_cache_page(url, cache_path):
    # Check if cache exists
    if os.path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8') as f:
            html = f.read()
        return html

    # If no cache, fetch it
    print(f"FETCH: {url}")
    
    # Send an honest user-agent
    req = urllib.request.Request(
        url, 
        headers={'User-Agent': 'FlyRankInternshipA9/1.0 (+https://github.com/mubashir72/The-polite-scraper)'}
    )
    
    try:
        # Set a timeout of 5 seconds
        with urllib.request.urlopen(req, timeout=5) as response:
            status = response.getcode()
            if status != 200:
                print(f"Failed to fetch {url}. Status code: {status}")
                return None
            
            html_bytes = response.read()
            html = html_bytes.decode('utf-8')
            
            # Ensure cache directory exists
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            
            # Save to cache
            with open(cache_path, 'w', encoding='utf-8') as f:
                f.write(html)
            
            return html
            
    except Exception as e:
        print(f"An error occurred while fetching {url}: {e}")
        return None

def extract_page_data(html, base_url):
    soup = BeautifulSoup(html, 'html.parser')
    book_links = []
    
    for h3 in soup.select('article.product_pod h3 a'):
        href = h3.get('href')
        if href:
            absolute_url = urljoin(base_url, href)
            book_links.append(absolute_url)
            
    next_link = None
    next_li = soup.select_one('li.next a')
    if next_li:
        href = next_li.get('href')
        next_link = urljoin(base_url, href)
        
    return book_links, next_link

def main():
    start_url = "https://books.toscrape.com/catalogue/page-1.html"
    current_url = start_url
    
    catalogue_pages = 0
    all_book_links = []
    max_pages = 3
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    while current_url and catalogue_pages < max_pages:
        catalogue_pages += 1
        
        # Determine safe filename for cache
        page_name = os.path.basename(current_url)
        if not page_name.endswith('.html'):
            page_name += '.html'
            
        cache_path = os.path.join(base_dir, "cache", page_name)
        
        is_cached = os.path.exists(cache_path)
        
        if not is_cached and catalogue_pages > 1:
            time.sleep(0.5) # Wait at least 0.5s between real requests
            
        html = fetch_and_cache_page(current_url, cache_path)
        if not html:
            break
            
        book_links, next_link = extract_page_data(html, current_url)
        all_book_links.extend(book_links)
        
        current_url = next_link
        
    unique_links = list(set(all_book_links))
    
    print(f"catalogue_pages={catalogue_pages}")
    print(f"discovered={len(all_book_links)}")
    print(f"unique_urls={len(unique_links)}")

if __name__ == "__main__":
    main()
