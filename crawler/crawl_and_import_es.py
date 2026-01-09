
import time
from datetime import datetime
from .factory import get_crawler
from elastic_indexer import ElasticIndexer


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
        """Run a single crawl cycle for all sources"""
        print(f"\n{'='*60}")
        print(f"Starting crawl cycle")
        print(f"{'='*60}\n")

        for crawler_info in self.crawlers:
            name = crawler_info['name']
            article_type = crawler_info['article_type']
            crawler = crawler_info['instance']

            print(f"\n--- {name} ({article_type}) ---")

            try:
                crawler.crawl_once()
                print(f"{name} completed")
            except Exception as e:
                print(f"{name} error: {e}")

        # Show stats
        self._show_stats()

    def _crawl_continuous(self):
        """Run continuous crawling for all sources"""
        cycle = 1

        while True:
            try:
                print(f"\n{'='*60}")
                print(f"CYCLE {cycle} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"{'='*60}")

                # Crawl all sources
                for crawler_info in self.crawlers:
                    name = crawler_info['name']
                    article_type = crawler_info['article_type']
                    crawler = crawler_info['instance']

                    print(f"\n--- {name} ({article_type}) ---")

                    try:
                        crawler.crawl_once()
                        print(f"{name} completed")
                    except Exception as e:
                        print(f"{name} error: {e}")

                # Show stats after each cycle
                self._show_stats()

                # Wait for next cycle
                print(f"\n{'='*60}")
                print(f"Next cycle in {self.crawl_interval}s")
                print(f"{'='*60}\n")
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

