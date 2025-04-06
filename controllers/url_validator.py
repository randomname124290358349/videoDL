import re


def is_valid_url(url):
    pattern = re.compile(
        r'^(?:http|https)://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    return bool(pattern.match(url))


def clean_url_list(urls):
    cleaned_urls = []

    if isinstance(urls, str):
        url_list = [url.strip() for url in urls.split('\n') if url.strip()]
    else:
        url_list = urls

    for url in url_list:
        if is_valid_url(url):
            cleaned_urls.append(url)

    return cleaned_urls