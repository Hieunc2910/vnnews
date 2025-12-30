import requests
import time
from bs4 import BeautifulSoup
from tqdm import tqdm
from logger import log
from crawler.base_crawler import BaseCrawler
from utils.bs4_utils import get_text_from_tag
from utils.date_utils import parse_vnexpress_date, is_recent_article


class VNExpressCrawler(BaseCrawler):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = log.get_logger(name=__name__)

    def extract_content(self, url):
        try:
            response = requests.get(url, timeout=20)
            soup = BeautifulSoup(response.content, "html.parser")

            title = soup.find("h1", class_="title-detail")
            if not title:
                return None, None, None, None

            date_tag = soup.find("span", class_="date")
            date = date_tag.text.strip() if date_tag else "N/A"

            desc = soup.find("p", class_="description")
            description = (get_text_from_tag(p) for p in desc.contents) if desc else ()

            paragraphs = (get_text_from_tag(p) for p in soup.find_all("p", class_="Normal"))

            return title.text, date, description, paragraphs
        except Exception as e:
            self.logger.debug(f"Extract error {url}: {e}")
            return None, None, None, None

    def write_content(self, url, output_fpath):
        title, date, description, paragraphs = self.extract_content(url)

        if not title:
            return False

        with open(output_fpath, "w", encoding="utf-8") as f:
            f.write(f"{title}\nNgày: {date}\n\n")
            for p in description:
                f.write(f"{p}\n")
            for p in paragraphs:
                f.write(f"{p}\n")
        return True

    def get_urls_of_type_thread(self, article_type, page_number):
        try:
            url = f"https://vnexpress.net/{article_type}-p{page_number}"
            response = requests.get(url, timeout=20)
            soup = BeautifulSoup(response.content, "html.parser")
            titles = soup.find_all(class_="title-news")

            if not titles:
                self.logger.debug(f"No articles on page {page_number}")
                return []

            return [t.find("a").get("href") for t in titles if t.find("a")]
        except Exception as e:
            self.logger.error(f"Page {page_number}: {e}")
            return []

    def get_urls_with_time_filter(self, article_type):
        """Lấy URLs với bộ lọc thời gian"""
        urls = []
        consecutive_old_pages = 0
        pbar = tqdm(desc="Pages", unit="p", ncols=70)

        for page in range(1, self.total_pages + 1):
            if consecutive_old_pages >= 3:
                self.logger.info(f"Stopped: 3 consecutive pages with old articles")
                break

            try:
                page_url = f"https://vnexpress.net/{article_type}-p{page}"
                response = requests.get(page_url, timeout=20)
                soup = BeautifulSoup(response.content, "html.parser")
                titles = soup.find_all(class_="title-news")

                if not titles:
                    break

                page_has_recent = False
                for title in titles:
                    link = title.find("a")
                    if not link:
                        continue
                    url = link.get("href")

                    time.sleep(0.5)  # Delay nhỏ

                    try:
                        art_response = requests.get(url, timeout=20)
                        art_soup = BeautifulSoup(art_response.content, "html.parser")
                        date_tag = art_soup.find("span", class_="date")

                        if date_tag and is_recent_article(date_tag.text.strip(), self.max_days_old, parse_vnexpress_date):
                            urls.append(url)
                            page_has_recent = True
                        elif not date_tag:
                            urls.append(url)
                            page_has_recent = True
                    except Exception as e:
                        self.logger.debug(f"Error checking {url}: {e}")
                        urls.append(url)
                        page_has_recent = True

                consecutive_old_pages = 0 if page_has_recent else consecutive_old_pages + 1
                pbar.update(1)

            except Exception as e:
                self.logger.error(f"Error on page {page}: {e}")
                break

        pbar.close()
        self.logger.info(f"Found {len(urls)} recent articles (≤{self.max_days_old} days)")
        return list(set(urls))