"""
Elasticsearch Indexer for real-time article indexing
Integrates with crawler to index articles as they are crawled
"""

import hashlib
import re
from datetime import datetime
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk


class ElasticIndexer:
    """Real-time indexer for crawled articles"""

    def __init__(self, es_url="http://localhost:9200", username=None, password=None, index_name="news_quansu"):
        """
            es_url: Elasticsearch URL
            username: Username for authentication (optional)
            password: Password for authentication (optional)
            index_name: Index name to use
        """
        self.es_url = es_url
        self.index_name = index_name

        # Create ES client
        if username and password:
            self.es = Elasticsearch(es_url, basic_auth=(username, password), request_timeout=30)
        else:
            self.es = Elasticsearch(es_url, request_timeout=30)

        # Ensure index exists
        self._ensure_index()

    def _ensure_index(self):
        """Tạo index đơn giản, Elasticsearch tự động xử lý mapping"""
        if self.es.indices.exists(index=self.index_name):
            return

        settings = {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "analysis": {
                    "analyzer": {
                        "vietnamese_analyzer": {
                            "type": "standard",
                            "stopwords": "_none_"
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "title": {"type": "text", "analyzer": "vietnamese_analyzer"},
                    "body": {"type": "text", "analyzer": "vietnamese_analyzer"},
                    "publish_date": {"type": "date", "format": "yyyy-MM-dd", "ignore_malformed": True},
                    "publish_date_str": {"type": "text"},
                    "source": {"type": "keyword"},
                    "category": {"type": "keyword"},
                    "url": {"type": "keyword"}
                }
            }
        }

        self.es.indices.create(index=self.index_name, body=settings)

    def parse_article_content(self, content, source, category, url):
        """Parse nội dung bài báo"""
        lines = content.strip().split('\n')
        if not lines:
            return None

        title = lines[0].strip()

        publish_date_str = ""
        publish_date = None
        if len(lines) > 1 and "Ngày:" in lines[1]:
            publish_date_str = lines[1].replace("Ngày:", "").strip()
            date_match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', publish_date_str)
            if date_match:
                day, month, year = date_match.groups()
                publish_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"

        body = "\n".join(lines[2:]).strip() if len(lines) > 2 else ""

        # Dùng title+source làm _id để tránh duplicate
        unique_key = f"{title}_{source}"
        doc_id = hashlib.md5(unique_key.encode()).hexdigest()

        return {
            "_id": doc_id,
            "title": title,
            "publish_date_str": publish_date_str,
            "publish_date": publish_date,
            "body": body,
            "source": source,
            "category": category,
            "url": url
        }

    def index_article(self, content, source, category, url):
        """
        Index a single article

        Args:
            content: Article content
            source: Source website
            category: Category
            url: Article URL

        Returns:
            True if successful, False otherwise
        """
        try:
            article = self.parse_article_content(content, source, category, url)
            if not article:
                return False

            doc_id = article.pop("_id")
            self.es.index(index=self.index_name, id=doc_id, document=article)
            return True
        except:
            return False

    def bulk_index_articles(self, articles):
        """
        Bulk index multiple articles

        Args:
            articles: List of article dicts

        Returns:
            Number of successfully indexed articles
        """
        actions = [
            {
                "_index": self.index_name,
                "_id": article["_id"],
                "_source": {k: v for k, v in article.items() if k != "_id"}
            }
            for article in articles
        ]

        success, failed = bulk(self.es, actions, stats_only=True, raise_on_error=False)
        return success

    def search(self, query, size=10, source=None, from_date=None, to_date=None):
        """Tìm kiếm bài báo với xử lý sai chính tả nhưng ưu tiên từ đúng"""
        must = []
        should = []

        if query:
            # Ưu tiên cao nhất: Match chính xác (boost 5)
            should.append({
                "multi_match": {
                    "query": query,
                    "fields": ["title^5", "body"],
                    "type": "best_fields",
                    "operator": "or",
                    "boost": 5
                }
            })

            # Ưu tiên thấp hơn: Match với fuzziness (boost 1)
            should.append({
                "multi_match": {
                    "query": query,
                    "fields": ["title^5", "body"],
                    "type": "best_fields",
                    "fuzziness": "AUTO",
                    "operator": "or",
                    "boost": 1
                }
            })

            # Phrase match (boost 10)
            should.append({
                "multi_match": {
                    "query": query,
                    "fields": ["title^10", "body^2"],
                    "type": "phrase",
                    "slop": 2,
                    "boost": 10
                }
            })

            # Bắt buộc ít nhất 1 trong các điều kiện should phải match
            must.append({
                "bool": {
                    "should": should,
                    "minimum_should_match": 1
                }
            })
            should = []  # Reset should cho bool ngoài

        if source:
            must.append({"term": {"source": source}})

        if from_date or to_date:
            date_range = {}
            if from_date:
                date_range["gte"] = from_date
            if to_date:
                date_range["lte"] = to_date
            must.append({"range": {"publish_date": date_range}})

        search_body = {
            "query": {
                "bool": {
                    "must": must if must else [{"match_all": {}}]
                }
            },
            "size": size,
            "sort": [
                "_score",
                {"publish_date": {"order": "desc", "unmapped_type": "date"}}
            ],
            "highlight": {
                "fields": {
                    "title": {
                        "pre_tags": ["<mark>"],
                        "post_tags": ["</mark>"],
                        "number_of_fragments": 0
                    },
                    "body": {
                        "pre_tags": ["<mark>"],
                        "post_tags": ["</mark>"],
                        "fragment_size": 150,
                        "number_of_fragments": 3
                    }
                }
            }
        }

        results = self.es.search(index=self.index_name, body=search_body)

        return [
            {
                **hit["_source"],
                "score": hit["_score"],
                "matched_in_title": hit.get("highlight", {}).get("title", []),
                "matched_in_body": hit.get("highlight", {}).get("body", [])
            }
            for hit in results["hits"]["hits"]
        ]


