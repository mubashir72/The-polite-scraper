import os
import urllib.request
from urllib.error import URLError, HTTPError

def fetch_and_cache_page(url, cache_path):
    # Check if cache exists
    if os.path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8') as f:
            html = f.read()
        print(f"CACHE HIT: {os.path.basename(cache_path)}")
        print(f"Size: {len(html)} bytes")
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
                print(f"Failed to fetch. Status code: {status}")
                return None
            
            html_bytes = response.read()
            html = html_bytes.decode('utf-8')
            
            # Ensure cache directory exists
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            
            # Save to cache
            with open(cache_path, 'w', encoding='utf-8') as f:
                f.write(html)
            
            print(f"Saved to cache. Size: {len(html)} bytes")
            return html
            
    except HTTPError as e:
        print(f"HTTP Error: {e.code} - {e.reason}")
    except URLError as e:
        print(f"URL Error: {e.reason}")
    except TimeoutError:
        print("Request timed out.")
    except Exception as e:
        print(f"An error occurred: {e}")
        
    return None

def main():
    url = "https://books.toscrape.com/catalogue/page-1.html"
    
    # Create absolute path to scraper/cache/catalogue-page-1.html
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cache_path = os.path.join(base_dir, "cache", "catalogue-page-1.html")
    
    html = fetch_and_cache_page(url, cache_path)

if __name__ == "__main__":
    main()
