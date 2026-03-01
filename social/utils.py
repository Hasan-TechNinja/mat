import requests
from bs4 import BeautifulSoup
import urllib.parse
import re

def fetch_amazon_product_data(url):
    """
    Fetches the product title and image URL from an Amazon product page.
    Returns a tuple: (title, image_url).
    If the fetch fails, returns (None, None).
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US, en;q=0.9',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Referer': 'https://www.google.com/'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        # We don't raise_for_status here because we want to fail gracefully 
        # instead of breaking post creation if Amazon returns 404/403 or blocks the request.
        if response.status_code != 200:
            return None, None
            
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract title
        title_tag = soup.find("span", attrs={"id": 'productTitle'})
        title = title_tag.get_text().strip() if title_tag else None
        
        # Extract image URL
        img_url = None
        # Try finding the landing image first
        img_tag = soup.find("img", attrs={"id": "landingImage"})
        if not img_tag:
            # Fallback to other possible main image identifiers
            img_tag = soup.find("img", attrs={"id": "imgBlkFront"})
            
        if img_tag:
            img_url = img_tag.get('src')
            # If the image uses data-a-dynamic-image, we can extract the highest res image
            dynamic_img = img_tag.get('data-a-dynamic-image')
            if dynamic_img:
                import json
                try:
                    urls_dict = json.loads(dynamic_img)
                    if urls_dict:
                        # Get the URL of the highest resolution image
                        img_url = max(urls_dict.items(), key=lambda x: x[1][0] * x[1][1])[0]
                except json.JSONDecodeError:
                    pass

        return title, img_url
        
    except Exception as e:
        # Silently fail, logs could be added here if needed
        print(f"Error fetching Amazon metadata: {e}")
        return None, None
