import requests
from bs4 import BeautifulSoup
from crawler.base_crawler import BaseCrawler
from utils.bs4_utils import get_text_from_tag


class VNExpressCrawler(BaseCrawler):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

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
        except:
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
            response = requests.get(url, timeout=30)
            soup = BeautifulSoup(response.content, "html.parser")

            titles = soup.find_all(class_="title-news")
            if not titles:
                return []

            return [t.find("a").get("href") for t in titles if t.find("a")]
        except:
            return []
