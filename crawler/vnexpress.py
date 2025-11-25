import requests
import sys
from pathlib import Path

from bs4 import BeautifulSoup

FILE = Path(__file__).resolve()
ROOT = FILE.parents[1]  # root directory
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))  # add ROOT to PATH

from logger import log
from crawler.base_crawler import BaseCrawler
from utils.bs4_utils import get_text_from_tag
from utils.date_utils import parse_vnexpress_date, is_recent_article


class VNExpressCrawler(BaseCrawler):

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.logger = log.get_logger(name=__name__)
        self.article_type_dict = {
            0: "thoi-su",
            1: "du-lich",
            2: "the-gioi",
            3: "kinh-doanh",
            4: "khoa-hoc",
            5: "giai-tri",
            6: "the-thao",
            7: "phap-luat",
            8: "giao-duc",
            9: "suc-khoe",
            10: "doi-song"
        }   

    def extract_content(self, url: str) -> tuple:
        """
        Extract title, description, publish date and paragraphs from url
        @param url (str): url to crawl
        @return title (str)
        @return publish_date (str)
        @return description (generator)
        @return paragraphs (generator)
        """
        content = requests.get(url).content
        soup = BeautifulSoup(content, "html.parser")

        title = soup.find("h1", class_="title-detail") 
        if title == None:
            return None, None, None, None
        title = title.text

        # Extract publish date
        date_tag = soup.find("span", class_="date")
        publish_date = date_tag.text.strip() if date_tag else "N/A"

        # some sport news have location-stamp child tag inside description tag
        description = (get_text_from_tag(p) for p in soup.find("p", class_="description").contents)
        paragraphs = (get_text_from_tag(p) for p in soup.find_all("p", class_="Normal"))

        return title, publish_date, description, paragraphs

    def write_content(self, url: str, output_fpath: str) -> bool:
        """
        From url, extract title, publish date, description and paragraphs then write in output_fpath
        @param url (str): url to crawl
        @param output_fpath (str): file path to save crawled result
        @return (bool): True if crawl successfully and otherwise
        """
        title, publish_date, description, paragraphs = self.extract_content(url)

        if title == None:
            return False

        with open(output_fpath, "w", encoding="utf-8") as file:
            file.write(title + "\n")
            file.write(f"Ngày xuất bản: {publish_date}\n")
            file.write("\n")
            for p in description:
                file.write(p + "\n")
            for p in paragraphs:                     
                file.write(p + "\n")

        return True

    def get_urls_of_type_thread(self, article_type, page_number):
        """" Get urls of articles in a specific type in a page"""
        # Support subcategory format: "the-gioi/quan-su"
        page_url = f"https://vnexpress.net/{article_type}-p{page_number}"
        content = requests.get(page_url).content
        soup = BeautifulSoup(content, "html.parser")
        titles = soup.find_all(class_="title-news")

        if (len(titles) == 0):
            self.logger.info(f"Couldn't find any news in {page_url} \nMaybe you sent too many requests, try using less workers")

        articles_urls = list()

        for title in titles:
            link = title.find_all("a")[0]
            articles_urls.append(link.get("href"))
    
        return articles_urls

    def get_urls_with_time_filter(self, article_type):
        """
        Get URLs with time-based filtering for VNExpress
        Stops when encountering too many old articles
        """
        from tqdm import tqdm

        articles_urls = []
        page = 1
        consecutive_old_pages = 0
        max_consecutive_old = 10  # Stop after 3 consecutive pages with all old articles

        self.logger.info(f"Crawling with time filter: max {self.max_days_old} days old")

        pbar = tqdm(desc="Pages (time-filtered)", unit="page")

        while page <= self.total_pages and consecutive_old_pages < max_consecutive_old:
            page_url = f"https://vnexpress.net/{article_type}-p{page}"

            try:
                content = requests.get(page_url).content
                soup = BeautifulSoup(content, "html.parser")
                titles = soup.find_all(class_="title-news")

                if len(titles) == 0:
                    self.logger.info(f"No articles found on page {page}")
                    break

                page_has_recent = False

                for title in titles:
                    link = title.find_all("a")[0]
                    url = link.get("href")

                    # Try to get date from article page
                    try:
                        article_content = requests.get(url).content
                        article_soup = BeautifulSoup(article_content, "html.parser")
                        date_tag = article_soup.find("span", class_="date")

                        if date_tag:
                            date_str = date_tag.text.strip()
                            if is_recent_article(date_str, self.max_days_old, parse_vnexpress_date):
                                articles_urls.append(url)
                                page_has_recent = True
                            else:
                                from utils.date_utils import get_days_old
                                days = get_days_old(date_str, parse_vnexpress_date)
                                self.logger.debug(f"Skipping old article ({days} days): {url}")
                        else:
                            # If no date found, include it to be safe
                            articles_urls.append(url)
                            page_has_recent = True
                    except Exception as e:
                        # If error getting article, include it to be safe
                        self.logger.debug(f"Error checking date for {url}: {e}")
                        articles_urls.append(url)
                        page_has_recent = True

                if page_has_recent:
                    consecutive_old_pages = 0
                else:
                    consecutive_old_pages += 1
                    self.logger.info(f"Page {page} has no recent articles ({consecutive_old_pages}/{max_consecutive_old})")

                page += 1
                pbar.update(1)

            except Exception as e:
                self.logger.error(f"Error crawling page {page}: {e}")
                break

        pbar.close()
        self.logger.info(f"Found {len(articles_urls)} recent articles from {page-1} pages")

        return list(set(articles_urls))

