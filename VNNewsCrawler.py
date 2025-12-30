import argparse
from logger import log
from utils import utils
from crawler.factory import get_crawler


def main(config_fpath):
    config = utils.get_config(config_fpath)
    log.setup_logging(log_dir=config["output_dpath"],
                      config_fpath=config.get("logger_fpath", "logger/logger_config.yml"))

    try:
        crawler = get_crawler(**config)
        crawler.start_crawling()
    except KeyboardInterrupt:
        print("\nStopped")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VN Military News Crawler")
    parser.add_argument("--config", default="config_vnexpress.yml", help="Config file")
    parser.add_argument("--interval", type=int, help="Interval (seconds)")
    parser.add_argument("--continuous", action="store_true", help="Continuous mode")

    args = parser.parse_args()
    main(args.config)