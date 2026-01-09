# Vietnamese Military News Crawler & Search Engine

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue)](https://www.python.org/)
[![Elasticsearch](https://img.shields.io/badge/Elasticsearch-8.x-green)](https://www.elastic.co/)
[![BeautifulSoup4](https://img.shields.io/badge/BeautifulSoup4-latest-purple)](https://pypi.org/project/beautifulsoup4/)

Hệ thống thu thập và tìm kiếm tin tức quân sự Việt Nam với Elasticsearch, hỗ trợ tìm kiếm tiếng Việt thông minh.

---

## Tính Năng

- **Crawl đa nguồn song song**: Thu thập đồng thời từ 4 báo lớn
- **Tìm kiếm tiếng Việt**: Xử lý có/không dấu, ranking thông minh
- **Tránh duplicate**: Dùng title+source làm ID duy nhất
- **Chế độ liên tục**: Tự động cập nhật theo chu kỳ
- **Highlight**: Trích đoạn và làm nổi từ khóa

---

## Cài Đặt

### 1. Python Dependencies

```bash
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 2. Elasticsearch

Download từ https://www.elastic.co/downloads/elasticsearch

```bash
# Windows
bin\elasticsearch.bat

# Linux/Mac
./bin/elasticsearch
```

Kiểm tra: `curl http://localhost:9200`

---

## Sử Dụng

### Crawl dữ liệu

```bash
python VNNewsCrawler.py --config config_quansu.yml
```

### Tìm kiếm

```bash
python search_news.py
```

Nhập từ khóa, hệ thống sẽ trả về top 10 bài báo với điểm số và lý do ranking.

### Xóa index cũ

```bash
python delete_index.py
```

---

## Cấu Hình

File `config_quansu.yml`:

```yaml
task: type
output_dpath: result

# Crawler settings
num_workers: 1          # 1 worker tránh bị chặn IP
total_pages: 3          # Số trang crawl mỗi nguồn

# Continuous mode
continuous_mode: true
crawl_interval: 300     # 5 phút
use_head_check: true

# Elasticsearch
enable_elastic: true
es_url: http://localhost:9200
es_index: news_quansu

# Nguồn tin
crawlers:
  - name: vnexpress
    article_type: the-gioi/quan-su
  - name: dantri
    article_type: the-gioi/quan-su
  - name: vietnamnet
    article_type: the-gioi/quan-su
  - name: qdnd
    article_type: quoc-te/quan-su-the-gioi
```

---

## Thuật Toán Thu Thập Dữ Liệu

### 1. Kiến Trúc Tổng Quan

```
┌─────────────────────────────────────────────────────────┐
│                    VNNewsCrawler                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │VNExpress │  │  DanTri  │  │VietnamNet│  │   QDND   │ │
│  │ Crawler  │  │ Crawler  │  │ Crawler  │  │ Crawler  │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘ │
│       └─────────────┴─────────────┴──────────────┘      │
│                         │                               │
│              ┌──────────▼──────────┐                    │
│              │  Parallel Threads   │                    │
│              │  (Threading Pool)   │                    │
│              └──────────┬──────────┘                    │
└─────────────────────────┼───────────────────────────────┘
                          │
                ┌─────────▼──────────┐
                │  HTML Parser       │
                │  (BeautifulSoup)   │
                └─────────┬──────────┘
                          │
                ┌─────────▼──────────┐
                │  Data Normalizer   │
                │  (Clean & Format)  │
                └─────────┬──────────┘
                          │
        ┌─────────────────┴─────────────────┐
        │                                   │
        ▼                                   ▼
┌───────────────┐                  ┌────────────────┐
│  File Storage │                  │ Elasticsearch  │
│  (result/)    │                  │  Index         │
└───────────────┘                  └────────────────┘
```

### 2. Thuật Toán Phát Hiện URLs

#### 2.1. VNExpress

```python
def get_urls_of_type_thread(article_type, page_number):
    """
    Phát hiện URLs từ VNExpress
    Pattern: https://vnexpress.net/the-gioi/quan-su-p{page}
    Selector: class="title-news"
    """
    url = f"https://vnexpress.net/{article_type}-p{page_number}"
    response = requests.get(url, timeout=30)
    soup = BeautifulSoup(response.content, "html.parser")
    
    # Tìm tất cả elements có class "title-news"
    titles = soup.find_all(class_="title-news")
    
    # Trích xuất href từ thẻ <a>
    return [t.find("a").get("href") for t in titles if t.find("a")]
```

**HTML Structure:**
```html
<h3 class="title-news">
    <a href="https://vnexpress.net/article-123.html">Title</a>
</h3>
```

#### 2.2. DanTri

```python
def get_urls_of_type_thread(article_type, page_number):
    """
    Phát hiện URLs từ DanTri
    Pattern: https://dantri.com.vn/the-gioi/quan-su/trang-{page}.htm
    Selector: class="article-title"
    """
    url = f"https://dantri.com.vn/{article_type}/trang-{page_number}.htm"
    response = requests.get(url, timeout=20)
    soup = BeautifulSoup(response.content, "html.parser")
    
    titles = soup.find_all(class_="article-title")
    
    urls = []
    for t in titles:
        link = t.find("a")
        if link:
            href = link.get("href")
            urls.append(href if href.startswith("http") else f"https://dantri.com.vn{href}")
    return urls
```

#### 2.3. VietnamNet

```python
def get_urls_of_type_thread(article_type, page_number):
    """
    Phát hiện URLs từ VietnamNet
    Pattern: https://vietnamnet.vn/the-gioi/quan-su-page{N-1}
    Selector: multiple classes
    """
    url = f"https://vietnamnet.vn/{article_type}" if page_number == 1 \
          else f"https://vietnamnet.vn/{article_type}-page{page_number - 1}"
    
    response = requests.get(url, timeout=15)
    soup = BeautifulSoup(response.content, "html.parser")
    
    # VietnamNet có nhiều class khác nhau cho title
    titles = soup.find_all(class_=[
        "horizontalPost__main-title",
        "vnn-title", 
        "title-bold"
    ])
    
    urls = []
    for title in titles:
        a_tag = title.find("a")
        if a_tag:
            href = a_tag.get("href")
            if href:
                full_url = href if href.startswith('http') \
                          else f"https://vietnamnet.vn{href}"
                urls.append(full_url)
    
    return list(set(urls))
```

**Đặc điểm:** VietnamNet có nhiều layout khác nhau, cần tìm theo nhiều class.

#### 2.4. QDND

```python
def get_urls_of_type_thread(article_type, page_number):
    """
    Phát hiện URLs từ QDND
    Pattern: https://www.qdnd.vn/quoc-te/quan-su-the-gioi/p/{page}
    Selector: <article> tag
    """
    url = f"https://www.qdnd.vn/{article_type}" if page_number == 1 \
          else f"https://www.qdnd.vn/{article_type}/p/{page_number}"
    
    response = requests.get(url, timeout=15)
    soup = BeautifulSoup(response.content, "html.parser")
    
    articles = soup.find_all("article")
    
    urls = []
    for art in articles:
        # Tìm link trong <h3> hoặc trực tiếp trong <article>
        h3 = art.find("h3")
        link = h3.find("a", href=True) if h3 else art.find("a", href=True)
        
        if link:
            href = link.get("href")
            if href.startswith('http'):
                urls.append(href)
            elif href.startswith('/'):
                urls.append(f"https://www.qdnd.vn{href}")
    
    return list(set(urls))
```

**HTML Structure:**
```html
<article>
    <h3>
        <a href="/quan-su-the-gioi/article-123">Title</a>
    </h3>
</article>
```

### 3. Thuật Toán Crawl Song Song

```python
class UnifiedCrawler:
    def _crawl_once(self):
        """Chạy song song 4 crawlers"""
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

    def _run_crawler(self, crawler_info):
        """Chạy một crawler trong thread riêng"""
        name = crawler_info['name']
        crawler = crawler_info['instance']
        
        with print_lock:  # Thread-safe printing
            print(f"[{name}] Starting...")
        
        try:
            crawler.crawl_once()
            with print_lock:
                print(f"[{name}] Completed")
        except Exception as e:
            with print_lock:
                print(f"[{name}] Error: {e}")
```

**Flow:**
```
Main Thread
    │
    ├──> Thread 1: VNExpress Crawler
    │         └──> Get URLs → Parse → Save → Index
    │
    ├──> Thread 2: DanTri Crawler
    │         └──> Get URLs → Parse → Save → Index
    │
    ├──> Thread 3: VietnamNet Crawler
    │         └──> Get URLs → Parse → Save → Index
    │
    └──> Thread 4: QDND Crawler
              └──> Get URLs → Parse → Save → Index
    │
    Wait all threads complete
    │
    Show statistics
```

### 4. Thuật Toán Trích Xuất Nội Dung

#### 4.1. Parse HTML Structure

Mỗi nguồn có cấu trúc HTML khác nhau:

| Nguồn | Title Selector | Date Selector | Content Selector |
|-------|----------------|---------------|------------------|
| VNExpress | `h1.title-detail` | `span.date` | `p.Normal` |
| DanTri | `h1.title-page.detail` | `time.author-time` | `div.singular-content p` |
| VietnamNet | `h1.content-detail-title` | `div.bread-crumb-detail__time` | `div.maincontent p` |
| QDND | `h1` or `meta[og:title]` | `script[ld+json]` | `div.articleContent p` |

#### 4.2. Thuật Toán Parse

```python
def extract_content(url):
    """
    Bước 1: Fetch HTML
    """
    response = requests.get(url, timeout=20)
    soup = BeautifulSoup(response.content, "html.parser")
    
    """
    Bước 2: Extract Title
    """
    title = soup.find("h1", class_="title-detail")
    if not title:
        return None, None, None, None
    
    """
    Bước 3: Extract Date
    """
    date_tag = soup.find("span", class_="date")
    date = date_tag.text.strip() if date_tag else "N/A"
    
    """
    Bước 4: Extract Description (Sapo/Lead)
    """
    desc = soup.find("p", class_="description")
    description = (get_text_from_tag(p) for p in desc.contents) if desc else ()
    
    """
    Bước 5: Extract Paragraphs
    """
    paragraphs = (get_text_from_tag(p) for p in soup.find_all("p", class_="Normal"))
    
    return title.text, date, description, paragraphs
```

#### 4.3. Làm Sạch Text

```python
def get_text_from_tag(tag):
    """
    Xử lý các trường hợp:
    - NavigableString: text thuần túy
    - Tag: extract text và loại bỏ HTML
    - None: return empty
    """
    if isinstance(tag, str):
        return tag.strip()
    elif hasattr(tag, 'text'):
        return tag.text.strip()
    return ""
```

### 5. Duy Trì Tính Cập Nhật

#### 5.1. Continuous Mode

```python
def _crawl_continuous(self):
    """Crawl liên tục theo chu kỳ"""
    cycle = 1
    
    while True:
        try:
            print(f"CYCLE {cycle} - {datetime.now()}")
            
            # Crawl tất cả sources
            threads = []
            for crawler_info in self.crawlers:
                thread = threading.Thread(
                    target=self._run_crawler,
                    args=(crawler_info,)
                )
                threads.append(thread)
                thread.start()
            
            for thread in threads:
                thread.join()
            
            # Hiển thị thống kê
            self._show_stats()
            
            # Chờ chu kỳ tiếp theo
            print(f"Next cycle in {self.crawl_interval}s")
            time.sleep(self.crawl_interval)
            cycle += 1
            
        except KeyboardInterrupt:
            print("Stopped by user")
            break
```

**Timeline:**
```
Cycle 1 (00:00)
    ├── Crawl 4 sources
    ├── Index to Elasticsearch
    └── Stats: 120 articles

Wait 5 minutes...

Cycle 2 (00:05)
    ├── Crawl 4 sources (new articles)
    ├── Index to Elasticsearch
    └── Stats: 125 articles (+5 new)

Wait 5 minutes...
...
```

#### 5.2. HEAD Check (Optional)

```python
def check_url_modified(url):
    """
    Kiểm tra URL có thay đổi không bằng HEAD request
    Tiết kiệm bandwidth
    """
    if not self.use_head_check:
        return True
    
    try:
        response = requests.head(url, timeout=10)
        
        # Hash ETag + Last-Modified
        hash_str = f"{response.headers.get('ETag', '')}" \
                   f"{response.headers.get('Last-Modified', '')}"
        url_hash = hashlib.md5(hash_str.encode()).hexdigest()
        
        # So sánh với hash cũ
        if url in self.url_hashes and self.url_hashes[url] == url_hash:
            return False  # Không thay đổi
        
        self.url_hashes[url] = url_hash
        return True  # Có thay đổi
    except:
        return True  # Lỗi = coi như có thay đổi
```

---

## Cơ Chế Elasticsearch

### 1. Index Mapping

```python
{
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
            "title": {
                "type": "text",
                "analyzer": "vietnamese_analyzer"
            },
            "body": {
                "type": "text",
                "analyzer": "vietnamese_analyzer"
            },
            "publish_date": {
                "type": "date",
                "format": "yyyy-MM-dd",
                "ignore_malformed": True
            },
            "publish_date_str": {"type": "text"},
            "source": {"type": "keyword"},
            "category": {"type": "keyword"},
            "url": {"type": "keyword"}
        }
    }
}
```

**Giải thích:**
- `vietnamese_analyzer`: Xử lý tiếng Việt (lowercase, tokenize)
- `keyword` type: Dùng cho filter và aggregation (không phân tích)
- `text` type: Dùng cho full-text search (có phân tích)
- `date` type: Dùng cho range query

### 2. Tránh Duplicate bằng Document ID

```python
def parse_article_content(content, source, category, url):
    """Parse và tạo unique ID"""
    # ... parse content ...
    
    # Tạo ID từ title + source
    unique_key = f"{title}_{source}"
    doc_id = hashlib.md5(unique_key.encode()).hexdigest()
    
    return {
        "_id": doc_id,
        "title": title,
        "body": body,
        "source": source,
        "category": category,
        "url": url,
        "publish_date": publish_date,
        "publish_date_str": publish_date_str
    }
```

**Flow:**
```
Article A (DanTri):
    Title: "Nga thử tên lửa mới"
    Source: "dantri"
    → doc_id = MD5("Nga thử tên lửa mới_dantri")
    → doc_id = "a1b2c3d4..."

Index lần 1:
    Elasticsearch tạo document với id="a1b2c3d4..."

Crawl lại (lần 2):
    Article A vẫn có cùng title + source
    → doc_id = "a1b2c3d4..." (giống lần 1)
    → Elasticsearch UPDATE thay vì CREATE
    → Không duplicate!
```

**Ưu điểm:**
- Cùng bài báo = cùng ID = không duplicate
- Tự động update nếu nội dung thay đổi
- Không phụ thuộc vào URL (URL có thể thay đổi)

### 3. Xử Lý Ngôn Ngữ Tiếng Việt

#### 3.1. Vietnamese Analyzer

```
Input: "Nga thử tên lửa đạn đạo mới"

Step 1: Standard Tokenizer
    → ["Nga", "thử", "tên", "lửa", "đạn", "đạo", "mới"]

Step 2: Lowercase Filter
    → ["nga", "thử", "tên", "lửa", "đạn", "đạo", "mới"]

Step 3: Store in Inverted Index
    nga     → [doc1, doc5, doc12]
    thử     → [doc1, doc8]
    tên     → [doc1, doc3, doc7]
    lửa     → [doc1, doc3, doc7]
    ...
```

#### 3.2. Search Flow

```
User Query: "ten lua" (không dấu)

Step 1: Analyze Query
    "ten lua" → ["ten", "lua"]

Step 2: Search in Index
    Elasticsearch tự động match:
    - "tên" matches "ten" (similar)
    - "lửa" matches "lua" (similar)

Step 3: Return Results
    Documents containing "tên lửa" được trả về
```

**Lưu ý:** Elasticsearch standard analyzer chưa hoàn hảo cho tiếng Việt. Để tốt hơn, nên:
- Dùng plugin Vietnamese Analyzer
- Hoặc dùng asciifolding filter
- Hoặc normalize ở application level

### 4. Cơ Chế Xếp Hạng (BM25)

#### 4.1. Thuật Toán BM25

```
score(D, Q) = ∑ IDF(qi) × (f(qi, D) × (k1 + 1)) / (f(qi, D) + k1 × (1 - b + b × |D| / avgdl))

Trong đó:
- D: Document
- Q: Query
- qi: Query term thứ i
- f(qi, D): Số lần qi xuất hiện trong D
- |D|: Độ dài document D
- avgdl: Độ dài trung bình của tất cả documents
- k1 = 1.2: Tuning parameter
- b = 0.75: Length normalization
- IDF: Inverse Document Frequency
```

#### 4.2. IDF (Inverse Document Frequency)

```
IDF(qi) = log((N - n(qi) + 0.5) / (n(qi) + 0.5))

Trong đó:
- N: Tổng số documents
- n(qi): Số documents chứa qi
```

**Ý nghĩa:**
- Từ hiếm (ít documents chứa) → IDF cao → Quan trọng hơn
- Từ phổ biến (nhiều documents chứa) → IDF thấp → Ít quan trọng

**Ví dụ:**
```
N = 1000 documents

Term "tên lửa":
    n("tên lửa") = 50 documents
    IDF = log((1000 - 50 + 0.5) / (50 + 0.5))
        = log(950.5 / 50.5)
        = log(18.8)
        = 2.93

Term "mới":
    n("mới") = 800 documents (rất phổ biến)
    IDF = log((1000 - 800 + 0.5) / (800 + 0.5))
        = log(200.5 / 800.5)
        = log(0.25)
        = -0.60 (gần 0)

→ "tên lửa" quan trọng hơn "mới" trong ranking
```

#### 4.3. Multi-field Boosting

```python
{
    "query": {
        "bool": {
            "should": [
                {
                    "match_phrase": {
                        "title": {
                            "query": "tên lửa",
                            "boost": 10  # Title boost x10
                        }
                    }
                },
                {
                    "match": {
                        "title": {
                            "query": "tên lửa",
                            "boost": 5   # Title partial boost x5
                        }
                    }
                },
                {
                    "match": {
                        "body": {
                            "query": "tên lửa",
                            "boost": 1   # Body boost x1
                        }
                    }
                }
            ],
            "minimum_should_match": 1
        }
    }
}
```

**Ý nghĩa:**
- Match trong **title exact phrase**: điểm × 10
- Match trong **title partial**: điểm × 5
- Match trong **body**: điểm × 1
- → Ưu tiên bài có từ khóa trong tiêu đề
