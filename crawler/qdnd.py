import requests
import json
import time
from bs4 import BeautifulSoup
from tqdm import tqdm
from logger import log
from crawler.base_crawler import BaseCrawler
from utils.bs4_utils import get_text_from_tag
from utils.date_utils import parse_qdnd_date, is_recent_article


class QDNDCrawler(BaseCrawler):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)  # Gọi __init__ của BaseCrawler trước
        self.logger = log.get_logger(name=__name__)
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

            # Tìm date theo nhiều cách
            date = "N/A"

            # 1. JSON-LD
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

            # 2. Thẻ time
            if date == "N/A":
                date_tag = soup.find("time")
                if date_tag:
                    date = date_tag.get("datetime") or date_tag.text.strip() or "N/A"

            # 3. Meta tag
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
            self.logger.debug(f"Extract error {url}: {e}")
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
        """Format ISO date sang định dạng tiếng Việt"""
        if not date_str or date_str == "N/A":
            return date_str

        try:
            dt = parse_qdnd_date(date_str)
            if not dt:
                return date_str

            weekdays = ["Thứ hai", "Thứ ba", "Thứ tư", "Thứ năm", "Thứ sáu", "Thứ bảy", "Chủ nhật"]
            weekday = weekdays[dt.weekday()]
            return f"{weekday}, {dt.strftime('%d/%m/%Y')}, {dt.strftime('%H:%M')} (GMT+7)"
        except:
            return date_str

    def get_urls_of_type_thread(self, article_type, page_number):
        try:
            url = f"{self.base_url}/{article_type}" if page_number == 1 else f"{self.base_url}/{article_type}/p/{page_number}"
            response = requests.get(url, timeout=20)
            soup = BeautifulSoup(response.content, "html.parser")
            articles = soup.find_all("article")

            if not articles:
                self.logger.debug(f"No articles on page {page_number}")
                return []

            urls = []
            for art in articles:
                h3 = art.find("h3")
                link = h3.find("a", href=True) if h3 else art.find("a", href=True)

                if link:
                    href = link.get("href")
                    if href.startswith('http'):
                        urls.append(href)
                    elif href.startswith('/'):
                        urls.append(self.base_url + href)
                    elif href.count('/') >= 2:
                        urls.append(f"{self.base_url}/{href}")

            return list(set(urls))
        except Exception as e:
            self.logger.error(f"Page {page_number}: {e}")
            return []

    def get_urls_with_time_filter(self, article_type):
        """Lấy URLs với bộ lọc thời gian - chỉ crawl đến khi gặp bài cũ"""
        urls = []
        consecutive_old_pages = 0
        pbar = tqdm(desc="Pages", unit="p", ncols=70)

        for page in range(1, self.total_pages + 1):
            # Dừng nếu 3 trang liên tiếp toàn bài cũ
            if consecutive_old_pages >= 3:
                self.logger.info(f"Stopped: 3 consecutive pages with old articles")
                break

            try:
                page_url = f"{self.base_url}/{article_type}" if page == 1 else f"{self.base_url}/{article_type}/p/{page}"
                response = requests.get(page_url, timeout=20)
                soup = BeautifulSoup(response.content, "html.parser")
                articles = soup.find_all("article")

                if not articles:
                    break

                page_has_recent = False
                for art in articles:
                    h3 = art.find("h3")
                    link = h3.find("a", href=True) if h3 else art.find("a", href=True)
                    if not link:
                        continue

                    href = link.get("href")
                    if href.startswith('http'):
                        url = href
                    elif href.startswith('/'):
                        url = self.base_url + href
                    elif href.count('/') >= 2:
                        url = f"{self.base_url}/{href}"
                    else:
                        continue

                    # Delay nhỏ giữa các request
                    time.sleep(0.5)

                    try:
                        art_response = requests.get(url, timeout=20)
                        art_soup = BeautifulSoup(art_response.content, "html.parser")

                        # Tìm date
                        date = None
                        for script in art_soup.find_all('script', type='application/ld+json'):
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

                        if not date:
                            date_tag = art_soup.find("time")
                            date = date_tag.get("datetime") or date_tag.text.strip() if date_tag else None

                        # Kiểm tra tuổi bài viết
                        if date and is_recent_article(date, self.max_days_old, parse_qdnd_date):
                            urls.append(url)
                            page_has_recent = True
                        elif not date:
                            # Không parse được date, thêm vào để an toàn
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