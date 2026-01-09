import requests
import json
from bs4 import BeautifulSoup
from crawler.base_crawler import BaseCrawler
from utils.bs4_utils import get_text_from_tag
from utils.date_utils import parse_qdnd_date


class QDNDCrawler(BaseCrawler):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.base_url = "https://www.qdnd.vn"

    def extract_content(self, url):
        try:
            response = requests.get(url, timeout=20)
            soup = BeautifulSoup(response.content, "html.parser")

            title = soup.find("h1")
            if not title:
                og_title = soup.find("meta", property="og:title")
                if not og_title:
                    return None, None, None, None
                title = og_title.get("content", "").strip()
            else:
                title = title.text.strip()

            date = "N/A"
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict) and 'datePublished' in data:
                        date = data['datePublished']
                        break
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and 'datePublished' in item:
                                date = item['datePublished']
                                break
                except:
                    pass

            if date == "N/A":
                date_tag = soup.find("time")
                if date_tag:
                    date = date_tag.get("datetime") or date_tag.text.strip() or "N/A"

            if date == "N/A":
                meta_date = soup.find("meta", property="article:published_time")
                if meta_date:
                    date = meta_date.get("content", "N/A")

            desc_tag = soup.find(
                class_=lambda x: x and any(k in str(x).lower() for k in ['sapo', 'lead', 'summary']) if x else False)
            description = (get_text_from_tag(p) for p in desc_tag.contents) if desc_tag else ()

            content = soup.find('div', class_='articleContent') or soup.find("article")
            paragraphs = (get_text_from_tag(p) for p in content.find_all("p")) if content else ()

            return title, date, description, paragraphs
        except Exception as e:
            return None, None, None, None

    def write_content(self, url, output_fpath):
        title, date, description, paragraphs = self.extract_content(url)
        if not title:
            return False

        with open(output_fpath, "w", encoding="utf-8") as f:
            f.write(f"{title}\nNgày: {self._format_date(date)}\n\n")
            for p in description:
                f.write(f"{p}\n")
            for p in paragraphs:
                f.write(f"{p}\n")
        return True

    def _format_date(self, date_str):
        if not date_str or date_str == "N/A":
            return date_str
        try:
            dt = parse_qdnd_date(date_str)
            if not dt:
                return date_str
            weekdays = ["Thứ hai", "Thứ ba", "Thứ tư", "Thứ năm", "Thứ sáu", "Thứ bảy", "Chủ nhật"]
            return f"{weekdays[dt.weekday()]}, {dt.strftime('%d/%m/%Y')}, {dt.strftime('%H:%M')} (GMT+7)"
        except:
            return date_str

    def get_urls_of_type_thread(self, article_type, page_number):
        try:
            url = f"{self.base_url}/{article_type}" if page_number == 1 else f"{self.base_url}/{article_type}/p/{page_number}"
            response = requests.get(url, timeout=15)
            soup = BeautifulSoup(response.content, "html.parser")
            articles = soup.find_all("article")

            urls = []
            for art in articles:
                h3 = art.find("h3")
                link = h3.find("a", href=True) if h3 else art.find("a", href=True)
                if link:
                    href = link.get("href")
                    if href.startswith('http'):
                        urls.append(href)
                    elif href.startswith('/'):
                        urls.append(f"{self.base_url}{href}")

            return list(set(urls))
        except:
            return []