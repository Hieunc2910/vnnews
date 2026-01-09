import requests
from bs4 import BeautifulSoup
from crawler.base_crawler import BaseCrawler
from utils.bs4_utils import get_text_from_tag


class DanTriCrawler(BaseCrawler):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.base_url = "https://dantri.com.vn"

    def extract_content(self, url):
        try:
            response = requests.get(url, timeout=20)
            soup = BeautifulSoup(response.content, "html.parser")

            title = soup.find("h1", class_="title-page detail")
            if not title:
                return None, None, None, None

            date_tag = soup.find("time", class_="author-time")
            date = date_tag.text.strip() if date_tag else "N/A"

            sapo = soup.find("h2", class_="singular-sapo")
            description = (get_text_from_tag(p) for p in sapo.contents) if sapo else ()

            content = soup.find("div", class_="singular-content")
            paragraphs = (get_text_from_tag(p) for p in content.find_all("p")) if content else ()

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
            url = f"https://dantri.com.vn/{article_type}/trang-{page_number}.htm"
            response = requests.get(url, timeout=20)
            soup = BeautifulSoup(response.content, "html.parser")
            titles = soup.find_all(class_="article-title")

            if not titles:
                return []

            urls = []
            for t in titles:
                link = t.find("a")
                if link:
                    href = link.get("href")
                    urls.append(href if href.startswith("http") else self.base_url + href)
            return urls
        except:
            return []
