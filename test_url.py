import urllib.parse
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

url = "https://www.amazon.co.uk/dp/B088W5HWVX/?tag=old-tag-20"
parsed = urlparse(url)
query_params = parse_qs(parsed.query)
query_params['tag'] = ['giftmedia-21']
new_query = urlencode(query_params, doseq=True)
new_url = parsed._replace(query=new_query).geturl()
print(new_url)
