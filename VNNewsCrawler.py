import argparse
from utils import utils
from crawler.factory import get_crawler
from crawler.crawl_and_import_es import UnifiedCrawler


def main(config_fpath):
    config = utils.get_config(config_fpath)

    try:
        # Check if unified mode (multiple crawlers)
        if 'crawlers' in config and config['crawlers']:
            print("Running in UNIFIED mode (multiple sources)")
            crawler = UnifiedCrawler(**config)
        else:
            print("Running in SINGLE mode")
            crawler = get_crawler(**config)

        crawler.start_crawling()
    except KeyboardInterrupt:
        print("\nStopped")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VN Military News Crawler")
    parser.add_argument("--config", default="config_quansu.yml", help="Config file")

    args = parser.parse_args()
    main(args.config)