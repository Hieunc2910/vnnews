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
from utils.date_utils import parse_vietnamnet_date, is_recent_article


class VietNamNetCrawler(BaseCrawler):

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.logger = log.get_logger(name=__name__)
        self.base_url = "https://vietnamnet.vn"
        self.article_type_dict = {
            0: "thoi-su",
            1: "kinh-doanh",
            2: "the-thao",
            3: "van-hoa",
            4: "giai-tri",
            5: "the-gioi",
            6: "doi-song",
            7: "giao-duc",
            8: "suc-khoe",
            9: "thong-tin-truyen-thong",
            10: "phap-luat",
            11: "oto-xe-may",
            12: "bat-dong-san",
            13: "du-lich",
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

        title_tag = soup.find("h1", class_="content-detail-title") 
        desc_tag = soup.find("h2", class_=["content-detail-sapo", "sm-sapo-mb-0"])
        p_tag = soup.find("div", class_=["maincontent", "main-content"])

        if [var for var in (title_tag, desc_tag, p_tag) if var is None]:
            return None, None, None, None

        title = title_tag.text

        # Extract publish date
        date_tag = soup.find("div", class_="bread-crumb-detail__time")
        publish_date = date_tag.text.strip() if date_tag else "N/A"

        description = (get_text_from_tag(p) for p in desc_tag.contents)
        paragraphs = (get_text_from_tag(p) for p in p_tag.find_all("p"))

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
        # VietnamNet uses format: /the-gioi/quan-su-pageX
        if "/" in article_type:
            page_url = f"https://vietnamnet.vn/{article_type}-page{page_number}"
        else:
            page_url = f"https://vietnamnet.vn/{article_type}-page{page_number}"

        content = requests.get(page_url).content
        soup = BeautifulSoup(content, "html.parser")
        titles = soup.find_all(class_=["horizontalPost__main-title", "vnn-title", "title-bold"])

        if (len(titles) == 0):
            self.logger.info(f"Couldn't find any news in {page_url} \nMaybe you sent too many requests, try using less workers")
            
        articles_urls = list()

        for title in titles:
            full_url = title.find_all("a")[0].get("href")
            if self.base_url not in full_url:
                full_url = self.base_url + full_url
            articles_urls.append(full_url)
    
        return articles_urls

    def get_urls_with_time_filter(self, article_type):
        """
        Get URLs with time-based filtering for VietnamNet
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
            page_url = f"https://vietnamnet.vn/{article_type}-page{page}"

            try:
                content = requests.get(page_url).content
                soup = BeautifulSoup(content, "html.parser")
                titles = soup.find_all(class_=["horizontalPost__main-title", "vnn-title", "title-bold"])

                if len(titles) == 0:
                    self.logger.info(f"No articles found on page {page}")
                    break

                page_has_recent = False

                for title in titles:
                    href = title.find_all("a")[0].get("href")
                    url = href if self.base_url in href else self.base_url + href

                    # Try to get date from article page
                    try:
                        article_content = requests.get(url).content
                        article_soup = BeautifulSoup(article_content, "html.parser")
                        date_tag = article_soup.find("div", class_="bread-crumb-detail__time")

                        if date_tag:
                            date_str = date_tag.text.strip()
                            if is_recent_article(date_str, self.max_days_old, parse_vietnamnet_date):
                                articles_urls.append(url)
                                page_has_recent = True
                            else:
                                from utils.date_utils import get_days_old
                                days = get_days_old(date_str, parse_vietnamnet_date)
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

