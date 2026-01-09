from .vnexpress import VNExpressCrawler
from .dantri import DanTriCrawler
from .vietnamnet import VietNamNetCrawler
from .qdnd import QDNDCrawler

CRAWLERS = {
    "vnexpress": VNExpressCrawler,
    "dantri": DanTriCrawler,
    "vietnamnet": VietNamNetCrawler,
    "qdnd": QDNDCrawler
}

def get_crawler(**kwargs):
    """Get crawler instance from config. Accepts 'crawler_name' or 'webname'."""
    crawler_name = kwargs.pop('crawler_name', None) or kwargs.pop('webname', None)
    if not crawler_name:
        raise ValueError("Config must contain 'crawler_name' or 'webname'")

    if crawler_name not in CRAWLERS:
        raise ValueError(f"Unknown crawler: {crawler_name}. Available: {list(CRAWLERS.keys())}")

    return CRAWLERS[crawler_name](**kwargs)
