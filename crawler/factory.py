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

def get_crawler(webname, **kwargs):
    return CRAWLERS[webname](**kwargs)