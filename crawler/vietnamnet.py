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
            random_delay(0.5, 2)
            response = requests.get(url, headers=get_headers(), timeout=20)
            response.encoding = 'utf-8'  # Fix encoding
            soup = BeautifulSoup(response.text, "html.parser")

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
            url = f"https://vietnamnet.vn/{article_type}" if page_number == 1 else f"https://vietnamnet.vn/{article_type}-page{page_number - 1}"
            response = requests.get(url, headers=get_headers(), timeout=20)
            response.encoding = 'utf-8'  # Fix encoding
            soup = BeautifulSoup(response.text, "html.parser")

            # Thử nhiều selectors khác nhau
            urls = []

            # Tìm tất cả links trong article tags
            articles = soup.find_all("article")
            for art in articles:
                link = art.find("a", href=True)
                if link and article_type in link['href']:
                    href = link['href']
                    full_url = href if self.base_url in href else self.base_url + href
                    urls.append(full_url)

            # Nếu không tìm thấy, thử tìm links trực tiếp
            if not urls:
                all_links = soup.find_all("a", href=True)
                for link in all_links:
                    href = link.get('href', '')
                    if article_type in href and 'vietnamnet.vn' in href:
                        urls.append(href)
                    elif article_type in href and href.startswith('/'):
                        urls.append(self.base_url + href)

            return list(set(urls))
        except:
            return []
