import os
from urllib.parse import urlparse, parse_qs
import requests


def extract_domain_and_surl(url):
    """
    Extracts the domain name and 'surl' value from a given URL.

    Args:
        url (str): The URL to extract domain name and 'surl' value from.

    Returns:
        tuple: A tuple containing the domain name and 'surl' value as (domain_name, surl_value).
    """

    return urlparse(url).netloc, parse_qs(urlparse(url).query).get('surl', [''])[0]


def parseCookieFile(cookiefile):
    """
    Parse cookies from a file in Netscape format.

    Args:
        cookiefile (str): Path to the cookies file.

    Returns:
        dict: A dictionary containing cookies as key-value pairs.
    """

    cookies = {}
    if not cookiefile or not os.path.exists(cookiefile):
        return cookies

    with open(cookiefile, 'r') as fp:
        for line in fp:
            if not line.startswith('#'):
                line_fields = line.strip().split('\t')
                # Make sure the line has at least 7 fields, as per Netscape format
                if len(line_fields) >= 7:
                    # Extract the cookie name and value
                    cookie_name = line_fields[5]
                    cookie_value = line_fields[6]
                    cookies[cookie_name] = cookie_value
    return cookies


def get_file_info(url: str, cookiefile: str = None):
    """
    Downloads metadata from a given URL and returns the file details including direct link.

    Args:
        url (str): The TeraBox share URL.
        cookiefile (str): Path to the cookies file.

    Returns:
        dict | None: A dictionary containing download information or None if unavailable.
    """

    axios = requests.Session()

    # Load cookies from provided file if available
    cookies = parseCookieFile(cookiefile or 'cookies.txt')
    if cookies:
        axios.cookies.update(cookies)

    response = axios.get(url, allow_redirects=True)
    domain, key = extract_domain_and_surl(response.url)

    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': f'https://{domain}/sharing/link?surl={key}',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36'
    }

    response = axios.get(
        f'https://www.terabox.com/share/list?app_id=250528&shorturl={key}&root=1', headers=headers)

    try:
        file_data = response.json().get('list', [])[0]
    except Exception:
        return None

    if not file_data or 'dlink' not in file_data:
        return None

    return {
        'direct_link': file_data.get('dlink'),
        'filename': file_data.get('server_filename'),
        'size': file_data.get('size'),
        'headers': headers,
        'cookies': cookies
    }


def download(url: str, cookiefile: str = None):
    """
    Wrapper to fetch only the direct download link from a TeraBox URL.

    Args:
        url (str): The TeraBox share URL.
        cookiefile (str): Path to the cookies file.

    Returns:
        str | None: The direct download link if available.
    """
    info = get_file_info(url, cookiefile=cookiefile)
    if not info:
        return None
    return info.get('direct_link')


if __name__ == "__main__":
    # Example usage when running the script directly
    dlink = download('https://teraboxapp.com/s/1ZqumlUbwrc32c40geaQsVg')
    print(dlink)
