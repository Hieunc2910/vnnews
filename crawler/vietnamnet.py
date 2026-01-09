import requests
from bs4 import BeautifulSoup
from crawler.base_crawler import BaseCrawler
from utils.bs4_utils import get_text_from_tag
from utils.anti_bot import get_headers, random_delay


class VietNamNetCrawler(BaseCrawler):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.base_url = "https://vietnamnet.vn"

    def extract_content(self, url):
        try:
            response = requests.get(url, timeout=20)
            soup = BeautifulSoup(response.content, "html.parser")

            title = soup.find("h1", class_="content-detail-title")
            if not title:
                return None, None, None, None

            date_tag = soup.find("div", class_="bread-crumb-detail__time")
            date = date_tag.text.strip() if date_tag else "N/A"

            desc = soup.find("h2", class_=["content-detail-sapo", "sm-sapo-mb-0"])
            description = (get_text_from_tag(p) for p in desc.contents) if desc else ()

            content = soup.find("div", class_=["maincontent", "main-content"])
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
            random_delay(1, 3)
            url = f"{self.base_url}/{article_type}" if page_number == 1 else f"{self.base_url}/{article_type}-page{page_number - 1}"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(response.text, "html.parser")

            urls = []
            title_classes = ["horizontalPost__main-title", "vnn-title", "title-bold"]
            titles = soup.find_all(class_=title_classes)

            for title in titles:
                a_tags = title.find_all("a")
                if a_tags:
                    href = a_tags[0].get("href")
                    if href and href.endswith('.html'):
                        full_url = href if href.startswith(
                            'http') else f"{self.base_url}{href if href.startswith('/') else '/' + href}"
                        urls.append(full_url)

            return list(set(urls))
        except:
            return []