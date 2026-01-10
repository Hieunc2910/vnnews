
import time
import threading
from datetime import datetime
from .factory import get_crawler
from elastic_indexer import ElasticIndexer

# Lock để tránh outputs bị lẫn lộn
print_lock = threading.Lock()


class UnifiedCrawler:

    def __init__(self, **kwargs):
        self.config = kwargs
        self.crawlers_config = kwargs.get('crawlers', [])

        # Shared settings
        self.continuous_mode = kwargs.get('continuous_mode', False)
        self.crawl_interval = kwargs.get('crawl_interval', 10800)
        self.output_dpath = kwargs.get('output_dpath', 'result')

        # Elasticsearch
        self.enable_elastic = kwargs.get('enable_elastic', False)
        self.elastic_indexer = None

        if self.enable_elastic:
            try:
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
                print(f"Elasticsearch: {es_url}/{es_index}")
            except Exception as e:
                print(f"Elasticsearch init failed: {e}")
                self.enable_elastic = False

        # Initialize crawlers
        self.crawlers = []
        self._init_crawlers()

    def _init_crawlers(self):

        for crawler_config in self.crawlers_config:
            try:
                crawler_name = crawler_config['name']
                article_type = crawler_config['article_type']

                # Create crawler-specific config
                config = {
                    **self.config,
                    'webname': crawler_name,
                    'article_type': article_type,
                    'output_dpath': f"{self.output_dpath}/{crawler_name}_quansu",
                    'continuous_mode': False,
                }

                # Remove crawlers list from individual config
                config.pop('crawlers', None)

                crawler = get_crawler(**config)
                self.crawlers.append({
                    'name': crawler_name,
                    'article_type': article_type,
                    'instance': crawler
                })

                print(f"{crawler_name:12} - {article_type}")

            except Exception as e:
                print(f"{crawler_config.get('name', 'Unknown'):12} - Failed: {e}")

        print(f"{'='*60}")
        print(f"Total crawlers: {len(self.crawlers)}")
        print(f"{'='*60}\n")

    def start_crawling(self):
        """Start crawling process"""
        if self.continuous_mode:
            self._crawl_continuous()
        else:
            self._crawl_once()

    def _crawl_once(self):
        """Chạy song song tất cả crawlers"""
        print(f"\n{'='*60}")
        print(f"Starting crawl cycle - PARALLEL MODE")
        print(f"{'='*60}\n")

        threads = []

        # Tạo thread cho mỗi crawler
        for crawler_info in self.crawlers:
            thread = threading.Thread(
                target=self._run_crawler,
                args=(crawler_info,),
                daemon=True
            )
            threads.append(thread)
            thread.start()

        # Chờ tất cả threads hoàn thành
        for thread in threads:
            thread.join()

        # Hiển thị thống kê
        self._show_stats()

    def _run_crawler(self, crawler_info):
        """Chạy một crawler trong thread riêng"""
        name = crawler_info['name']
        article_type = crawler_info['article_type']
        crawler = crawler_info['instance']

        with print_lock:
            print(f"\n[{name}] Starting ({article_type})...")

        try:
            crawler.crawl_once()
            with print_lock:
                print(f"[{name}] Completed")
        except Exception as e:
            with print_lock:
                print(f"[{name}] Error: {e}")


    def _crawl_continuous(self):
        """Chạy liên tục với chế độ song song"""
        cycle = 1

        while True:
            try:
                print(f"CYCLE {cycle} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

                threads = []

                # Tạo thread cho mỗi crawler
                for crawler_info in self.crawlers:
                    thread = threading.Thread(
                        target=self._run_crawler,
                        args=(crawler_info,),
                        daemon=True
                    )
                    threads.append(thread)
                    thread.start()

                # Chờ tất cả threads hoàn thành
                for thread in threads:
                    thread.join()

                self._show_stats()
                time.sleep(self.crawl_interval)
                cycle += 1

            except KeyboardInterrupt:
                print("\n\nStopped by user")
                break
            except Exception as e:
                print(f"\nCycle error: {e}")
                print("Retrying in 60s...")
                time.sleep(60)

    def _show_stats(self):
        """Show statistics after crawl cycle"""
        print(f"\n{'='*60}")
        print("STATISTICS")
        print(f"{'='*60}")

        # Count articles from Elasticsearch
        if self.enable_elastic and self.elastic_indexer:
            try:
                # Get document count
                count = self.elastic_indexer.es.count(index=self.elastic_indexer.index_name)
                total_docs = count['count']

                print(f"Total articles in Elasticsearch: {total_docs}")

                # Count by source
                aggs_query = {
                    "size": 0,
                    "aggs": {
                        "by_source": {
                            "terms": {
                                "field": "source",
                                "size": 100
                            }
                        }
                    }
                }

                result = self.elastic_indexer.es.search(
                    index=self.elastic_indexer.index_name,
                    body=aggs_query
                )

                print("\nBy source:")
                for bucket in result['aggregations']['by_source']['buckets']:
                    source = bucket['key']
                    count = bucket['doc_count']
                    print(f"  {source:12} : {count:5} articles")

            except Exception as e:
                print(f"Could not retrieve stats: {e}")
        else:
            print("Elasticsearch not enabled")

        print(f"{'='*60}\n")

