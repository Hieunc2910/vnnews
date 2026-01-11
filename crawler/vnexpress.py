import requests
from bs4 import BeautifulSoup
from crawler.base_crawler import BaseCrawler
from utils.bs4_utils import get_text_from_tag


class VNExpressCrawler(BaseCrawler):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.consecutive_timeouts = 0
        self.is_blocked = False

    def reset_blocked_status(self):
        """Reset trạng thái bị chặn cho cycle mới"""
        self.consecutive_timeouts = 0
        self.is_blocked = False

    def extract_content(self, url):
        if self.is_blocked:
            return None, None, None, None

        try:
            response = requests.get(url, timeout=20)
            soup = BeautifulSoup(response.content, "html.parser")

            title = soup.find("h1", class_="title-detail")
            if not title:
                self.consecutive_timeouts = 0
                return None, None, None, None

            date_tag = soup.find("span", class_="date")
            date = date_tag.text.strip() if date_tag else "N/A"

            desc = soup.find("p", class_="description")
            description = (get_text_from_tag(p) for p in desc.contents) if desc else ()

            paragraphs = (get_text_from_tag(p) for p in soup.find_all("p", class_="Normal"))

            self.consecutive_timeouts = 0
            return title.text, date, description, paragraphs
        except requests.exceptions.Timeout:
            self.consecutive_timeouts += 1
            if self.consecutive_timeouts >= 3:
                self.is_blocked = True
            return None, None, None, None
        except:
            self.consecutive_timeouts = 0
            return None, None, None, None

    def write_content(self, url, output_fpath):
        if self.is_blocked:
            return False

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
        if self.is_blocked:
            return []

        try:
            url = f"https://vnexpress.net/{article_type}-p{page_number}"
            response = requests.get(url, timeout=30)
            soup = BeautifulSoup(response.content, "html.parser")

            titles = soup.find_all(class_="title-news")
            if not titles:
                return []

            self.consecutive_timeouts = 0
            return [t.find("a").get("href") for t in titles if t.find("a")]
        except requests.exceptions.Timeout:
            self.consecutive_timeouts += 1
            if self.consecutive_timeouts >= 3:
                self.is_blocked = True
            return []
        except:
            self.consecutive_timeouts = 0
            return []
