from abc import ABC, abstractmethod
import concurrent.futures
import time
import hashlib
import requests
from datetime import datetime
from tqdm import tqdm
from utils.utils import init_output_dirs, create_dir, read_file


class BaseCrawler(ABC):

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

        # Tracking cho continuous mode
        self.crawled_urls = set()
        self.url_hashes = {}

        # Config cho continuous crawling
        self.continuous_mode = kwargs.get('continuous_mode', False)
        self.crawl_interval = kwargs.get('crawl_interval', 10800)  # 3 giờ
        self.use_head_check = kwargs.get('use_head_check', False)  # Mặc định TẮT

    @abstractmethod
    def extract_content(self, url):
        """
        Extract title, description and paragraphs from url
        @param url (str): url to crawl
        @return title (str)
        @return description (generator)
        @return paragraphs (generator)
        """
        title = str()
        description = list()
        paragraphs = list()
        return title, description, paragraphs

    @abstractmethod
    def write_content(self, url, output_fpath):
        """
        From url, extract title, description and paragraphs then write in output_fpath
        @param url (str): url to crawl
        @param output_fpath (str): file path to save crawled result
        @return (bool): True if crawl successfully and otherwise
        """
        return True

    @abstractmethod
    def get_urls_of_type_thread(self, article_type, page_number):
        """" Get urls of articles in a specific type in a page"""
        articles_urls = list()
        return articles_urls

    def start_crawling(self):
        if self.continuous_mode:
            self.crawl_continuous()
        else:
            self.crawl_once()

    def crawl_once(self):
        """Chạy một lần crawl"""
        error_urls = list()
        if self.task == "url":
            error_urls = self.crawl_urls(self.urls_fpath, self.output_dpath)
        elif self.task == "type":
            error_urls = self.crawl_types()

        self.logger.info(f"The number of failed URL: {len(error_urls)}")

    def crawl_continuous(self):
        """Chạy crawl liên tục theo chu kỳ"""
        cycle = 1
        while True:
            try:
                self.logger.info(f"=== Cycle {cycle} - {datetime.now().strftime('%H:%M:%S %d/%m/%Y')} ===")
                self.crawl_once()
                self.logger.info(f"Next cycle in {self.crawl_interval}s ({self.crawl_interval // 60} minutes)")
                time.sleep(self.crawl_interval)
                cycle += 1
            except KeyboardInterrupt:
                self.logger.info("Crawler stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Error in cycle {cycle}: {e}")
                self.logger.info("Retrying in 60s...")
                time.sleep(60)

    def check_url_modified(self, url):
        """Kiểm tra URL có thay đổi không bằng HEAD request"""
        if not self.use_head_check:
            return True

        try:
            response = requests.head(url, timeout=10, allow_redirects=True)
            # Tạo hash từ ETag và Last-Modified
            hash_str = f"{response.headers.get('ETag', '')}{response.headers.get('Last-Modified', '')}"
            url_hash = hashlib.md5(hash_str.encode()).hexdigest()

            # So sánh với hash cũ
            if url in self.url_hashes and self.url_hashes[url] == url_hash:
                return False  # Không thay đổi

            self.url_hashes[url] = url_hash
            return True  # Có thay đổi hoặc chưa check bao giờ
        except:
            return True  # Nếu lỗi, cứ crawl

    def crawl_urls(self, urls_fpath, output_dpath):
        """
        Crawling contents from a list of urls
        Returns:
            list of failed urls
        """
        self.logger.info(f"Start crawling urls from {urls_fpath} file...")
        create_dir(output_dpath)
        urls = list(read_file(urls_fpath))

        # Lọc bỏ URLs đã crawl (nếu dùng continuous mode)
        if self.continuous_mode:
            urls = [u for u in urls if u not in self.crawled_urls]
            if not urls:
                self.logger.info("No new URLs to crawl")
                return []

        num_urls = len(urls)
        self.logger.info(f"Crawling {num_urls} URLs...")

        # number of digits in an integer
        self.index_len = len(str(num_urls))

        args = ([output_dpath] * num_urls, urls, range(num_urls))
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            results = list(tqdm(executor.map(self.crawl_url_thread, *args), total=num_urls, desc="URLs"))

        self.logger.info(f"Saving crawling result into {output_dpath} directory...")
        return [result for result in results if result is not None]

    def crawl_url_thread(self, output_dpath, url, index):
        """ Crawling content of the specific url """

        # Kiểm tra đã crawl chưa (continuous mode)
        if url in self.crawled_urls:
            return None

        # Kiểm tra URL có thay đổi không (HEAD check)
        if not self.check_url_modified(url):
            self.logger.debug(f"URL not modified, skipping: {url}")
            return None

        file_index = str(index + 1).zfill(self.index_len)
        output_fpath = "".join([output_dpath, "/url_", file_index, ".txt"])
        is_success = self.write_content(url, output_fpath)

        if is_success:
            self.crawled_urls.add(url)  # Đánh dấu đã crawl
            return None
        else:
            self.logger.debug(f"Crawling unsuccessfully: {url}")
            return url

    def crawl_types(self):
        """ Crawling contents of a specific type or all types """
        urls_dpath, results_dpath = init_output_dirs(self.output_dpath)

        if self.article_type == "all":
            error_urls = self.crawl_all_types(urls_dpath, results_dpath)
        else:
            error_urls = self.crawl_type(self.article_type, urls_dpath, results_dpath)
        return error_urls

    def crawl_type(self, article_type, urls_dpath, results_dpath):
        """" Crawl total_pages of articles in specific type """
        self.logger.info(f"Crawl articles type {article_type}")
        error_urls = list()

        # getting urls
        self.logger.info(f"Getting urls of {article_type}...")
        articles_urls = self.get_urls_of_type(article_type)

        # Replace / with _ for file/folder names to avoid directory issues
        safe_article_type = article_type.replace("/", "_")

        articles_urls_fpath = "/".join([urls_dpath, f"{safe_article_type}.txt"])
        with open(articles_urls_fpath, "w") as urls_file:
            urls_file.write("\n".join(articles_urls))

            # crawling urls
        self.logger.info(f"Crawling from urls of {article_type}...")
        results_type_dpath = "/".join([results_dpath, safe_article_type])
        error_urls = self.crawl_urls(articles_urls_fpath, results_type_dpath)

        return error_urls

    def crawl_all_types(self, urls_dpath, results_dpath):
        """" Crawl articles from all categories with total_pages per category """
        total_error_urls = list()

        num_types = len(self.article_type_dict)
        for i in range(num_types):
            article_type = self.article_type_dict[i]
            error_urls = self.crawl_type(article_type, urls_dpath, results_dpath)
            self.logger.info(f"The number of failed {article_type} URL: {len(error_urls)}")
            self.logger.info("-" * 79)
            total_error_urls.extend(error_urls)

        return total_error_urls

    def get_urls_of_type(self, article_type):
        """" Get urls of articles in a specific type """
        articles_urls = list()

        # If max_days_old is set, use time-based filtering
        if hasattr(self, 'max_days_old') and self.max_days_old is not None:
            # Check if child class implements get_urls_with_time_filter
            if hasattr(self, 'get_urls_with_time_filter') and callable(getattr(self, 'get_urls_with_time_filter')):
                articles_urls = self.get_urls_with_time_filter(article_type)
            else:
                self.logger.warning("Time-based filtering requested but not implemented, falling back to page-based")
                articles_urls = self._get_urls_without_filter(article_type)
        else:
            # Original behavior: crawl all pages
            articles_urls = self._get_urls_without_filter(article_type)

        return articles_urls

    def _get_urls_without_filter(self, article_type):
        """Get URLs without time filtering (original behavior)"""
        args = ([article_type] * self.total_pages, range(1, self.total_pages + 1))
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            results = list(
                tqdm(executor.map(self.get_urls_of_type_thread, *args), total=self.total_pages, desc="Pages"))

        articles_urls = sum(results, [])
        return list(set(articles_urls))