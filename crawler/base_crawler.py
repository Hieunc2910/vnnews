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

        # Tracking for continuous mode
        self.crawled_urls = set()
        self.url_hashes = {}

        # Config for continuous crawling
        self.continuous_mode = kwargs.get('continuous_mode', False)
        self.crawl_interval = kwargs.get('crawl_interval', 10800)  # 3 hours
        self.use_head_check = kwargs.get('use_head_check', False)

        # Elasticsearch indexing
        self.enable_elastic = kwargs.get('enable_elastic', False)
        self.elastic_indexer = None
        if self.enable_elastic:
            try:
                from elastic_indexer import ElasticIndexer
                es_url = kwargs.get('es_url', 'http://localhost:9200')
                es_username = kwargs.get('es_username')
                es_password = kwargs.get('es_password')
                es_index = kwargs.get('es_index', 'news_quansu')

                self.elastic_indexer = ElasticIndexer(
                    es_url=es_url,
                    username=es_username,
                    password=es_password,
                    index_name=es_index
                )
            except Exception as e:
                print(f"Elasticsearch init failed: {e}")
                self.enable_elastic = False

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
        """Run a single crawl cycle"""
        if self.task == "url":
            error_urls = self.crawl_urls(self.urls_fpath, self.output_dpath)
        elif self.task == "type":
            error_urls = self.crawl_types()
        else:
            error_urls = []

        if error_urls:
            print(f"Failed URLs: {len(error_urls)}")

    def crawl_continuous(self):
        """Run continuous crawling with periodic intervals"""
        cycle = 1
        while True:
            try:
                print(f"\nCycle {cycle} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                self.crawl_once()
                print(f"Next cycle in {self.crawl_interval}s")
                time.sleep(self.crawl_interval)
                cycle += 1
            except KeyboardInterrupt:
                print("\nStopped by user")
                break
            except Exception as e:
                print(f"Cycle error: {e}")
                time.sleep(60)

    def check_url_modified(self, url):
        """Check if URL has been modified using HEAD request"""
        if not self.use_head_check:
            return True

        try:
            response = requests.head(url, timeout=10, allow_redirects=True)
            hash_str = f"{response.headers.get('ETag', '')}{response.headers.get('Last-Modified', '')}"
            url_hash = hashlib.md5(hash_str.encode()).hexdigest()

            if url in self.url_hashes and self.url_hashes[url] == url_hash:
                return False

            self.url_hashes[url] = url_hash
            return True
        except:
            return True

    def crawl_urls(self, urls_fpath, output_dpath):
        """Crawl contents from a list of urls. Returns list of failed urls."""
        create_dir(output_dpath)
        urls = list(read_file(urls_fpath))

        if self.continuous_mode:
            urls = [u for u in urls if u not in self.crawled_urls]
            if not urls:
                print("No new URLs to crawl")
                return []

        num_urls = len(urls)
        print(f"Crawling {num_urls} URLs...")

        self.index_len = len(str(num_urls))

        args = ([output_dpath] * num_urls, urls, range(num_urls))
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            results = list(tqdm(executor.map(self.crawl_url_thread, *args), total=num_urls, desc="URLs"))

        return [result for result in results if result is not None]

    def crawl_url_thread(self, output_dpath, url, index):
        """Crawl content of the specific url"""
        if url in self.crawled_urls:
            return None

        if not self.check_url_modified(url):
            return None

        file_index = str(index + 1).zfill(self.index_len)
        output_fpath = "".join([output_dpath, "/url_", file_index, ".txt"])
        is_success = self.write_content(url, output_fpath)

        if is_success:
            self.crawled_urls.add(url)

            # Index to Elasticsearch if enabled
            if self.enable_elastic and self.elastic_indexer:
                try:
                    with open(output_fpath, 'r', encoding='utf-8') as f:
                        content = f.read()

                    source = self.__class__.__name__.replace('Crawler', '').lower()
                    category = output_dpath.split('/')[-1] if '/' in output_dpath else output_dpath.split('\\')[-1]

                    self.elastic_indexer.index_article(content, source, category, url)
                except:
                    pass

            return None
        else:
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
        error_urls = list()

        # getting urls
        print(f"Getting URLs from {article_type}...")
        articles_urls = self.get_urls_of_type(article_type)
        print(f"Found {len(articles_urls)} unique URLs")

        # Replace / with _ for file/folder names to avoid directory issues
        safe_article_type = article_type.replace("/", "_")

        articles_urls_fpath = "/".join([urls_dpath, f"{safe_article_type}.txt"])
        with open(articles_urls_fpath, "w", encoding="utf-8") as urls_file:
            urls_file.write("\n".join(articles_urls))

        # crawling urls
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
            if error_urls:
                print(f"{article_type}: {len(error_urls)} failed URLs")
            total_error_urls.extend(error_urls)

        return total_error_urls

    def get_urls_of_type(self, article_type):
        """Get urls of articles in a specific type"""
        args = ([article_type] * self.total_pages, range(1, self.total_pages + 1))
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            results = list(
                tqdm(executor.map(self.get_urls_of_type_thread, *args), total=self.total_pages, desc="Pages"))

        articles_urls = sum(results, [])
        return list(set(articles_urls))