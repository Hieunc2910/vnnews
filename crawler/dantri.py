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
from utils.date_utils import parse_dantri_date, is_recent_article


class DanTriCrawler(BaseCrawler):

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.logger = log.get_logger(name=__name__)
        self.base_url = "https://dantri.com.vn"
        self.article_type_dict = {
            0: "xa-hoi",
            1: "the-gioi",
            2: "kinh-doanh",
            3: "bat-dong-san",
            4: "the-thao",
            5: "lao-dong-viec-lam",
            6: "tam-long-nhan-ai",
            7: "suc-khoe",
            8: "van-hoa",
            9: "giai-tri",
            10: "suc-manh-so",
            11: "giao-duc",
            12: "an-sinh",
            13: "phap-luat"
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

        title = soup.find("h1", class_="title-page detail") 
        if title == None:
            return None, None, None, None
        title = title.text

        # Extract publish date
        date_tag = soup.find("time", class_="author-time")
        publish_date = date_tag.text.strip() if date_tag else "N/A"

        description = (get_text_from_tag(p) for p in soup.find("h2", class_="singular-sapo").contents)
        content = soup.find("div", class_="singular-content")
        paragraphs = (get_text_from_tag(p) for p in content.find_all("p"))

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
        # Check if article_type contains "/" for subcategory
        if "/" in article_type:
            page_url = f"https://dantri.com.vn/{article_type}/trang-{page_number}.htm"
        else:
            page_url = f"https://dantri.com.vn/{article_type}/trang-{page_number}.htm"

        content = requests.get(page_url).content
        soup = BeautifulSoup(content, "html.parser")
        titles = soup.find_all(class_="article-title")

        if (len(titles) == 0):
            self.logger.info(f"Couldn't find any news in {page_url} \nMaybe you sent too many requests, try using less workers")
            

        articles_urls = list()

        for title in titles:
            link = title.find_all("a")[0]
            href = link.get("href")
            # Check if href is already a full URL
            if href.startswith("http"):
                articles_urls.append(href)
            else:
                articles_urls.append(self.base_url + href)

        return articles_urls

    def get_urls_with_time_filter(self, article_type):
        """
        Get URLs with time-based filtering for DanTri
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
            page_url = f"https://dantri.com.vn/{article_type}/trang-{page}.htm"

            try:
                content = requests.get(page_url).content
                soup = BeautifulSoup(content, "html.parser")
                titles = soup.find_all(class_="article-title")

                if len(titles) == 0:
                    self.logger.info(f"No articles found on page {page}")
                    break

                page_has_recent = False

                for title in titles:
                    link = title.find_all("a")[0]
                    href = link.get("href")
                    url = href if href.startswith("http") else self.base_url + href

                    # Try to get date from article page
                    try:
                        article_content = requests.get(url).content
                        article_soup = BeautifulSoup(article_content, "html.parser")
                        date_tag = article_soup.find("time", class_="author-time")

                        if date_tag:
                            date_str = date_tag.text.strip()
                            if is_recent_article(date_str, self.max_days_old, parse_dantri_date):
                                articles_urls.append(url)
                                page_has_recent = True
                            else:
                                from utils.date_utils import get_days_old
                                days = get_days_old(date_str, parse_dantri_date)
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

