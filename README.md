# 📰 Vietnamese news crawler
[![Python 3.10.7](https://img.shields.io/badge/python-3.10.7-blue)](https://www.python.org/downloads/release/python-3107/)
[![BeautifulSoup 0.0.1](https://img.shields.io/badge/BeautifulSoup-0.0.1-purple)](https://pypi.org/project/bs4/)
[![Requests 2.28.1](https://img.shields.io/badge/Requests-2.28.1-black)](https://pypi.org/project/requests/)
[![tqdm 4.64.1](https://img.shields.io/badge/tqdm-4.64.1-orange)](https://pypi.org/project/tqdm/)  

Crawling titles and paragraphs of Vietnamese online articles using their **URLs** or categories names 

Current supported websites:
- [VNExpress](https://vnexpress.net/)
- [DanTri](https://dantri.com.vn/)
- [VietNamNet](https://vietnamnet.vn/)

## 🧰 Installation
Create virtual environment then install required packages:
```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## 👨‍💻 Usage
Modifying your crawler configuration file (default is `crawler_config.yml`) to customize your crawling progress.

```yml
# crawler_config.yml

# Name of news website that want to crawls (vnexpress, dantri, vietnamnet)
webname: "vnexpress"

# tasks = ["url", "type"]
task: "url"

#logger config file path
logger_fpath: "logger/logger_config.yml"
urls_fpath: "urls.txt"
output_dpath: "result"
num_workers: 1

# if task == "type": 
# article_type == "all" to crawl all of types
article_type: "du-lich"
total_pages: 1

# Time-based filtering: only crawl articles from the last X days
# Set to null or remove to crawl all pages (default behavior)
max_days_old: 7
```

Then simply run:
```
python VNNewsCrawler.py --config crawler_config.yml
```

### ⏰ Time-based Filtering (New!)
You can now filter articles by their publication date using the `max_days_old` parameter:
- Set `max_days_old: 7` to only crawl articles published in the last 7 days
- Set `max_days_old: null` or remove the parameter to crawl all pages (default behavior)
- The crawler will automatically stop when it encounters multiple consecutive pages with only old articles

**Example:** To crawl only recent military news from the last 7 days:
```yml
webname: "vnexpress"
task: "type"
article_type: "the-gioi/quan-su"
total_pages: 10
max_days_old: 7  # Only articles from last 7 days
```

This is especially useful when you want to avoid crawling hundreds of old articles and only get the latest news.
### Crawl by URL
To perform URL-based crawling, you need to configure the file by setting `task: "url"`. The program will proceed to crawl each URL specified in the `urls_fpath` file. By default, the program is equipped with two VNExpress news URLs included in the `urls.txt` file.

### Crawl by category name
To crawl URLs based on their categories, you need to set `task: "type"` in the configuration file. The program will retrieve URLs from a specified number of pages (`total_pages`) belonging to the provided category. Currently, my program supports only the following categories for these websites:

| VNExpress                                                                                                                                                           | DanTri                                                                                                                                                                                                                                    | VietNamNet                                                                                                                                                                                                                             |
|---------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 0. thoi-su<br>1. du-lich<br>2. the-gioi<br>3. kinh-doanh<br>4. khoa-hoc<br>5. giai-tri<br>6. the-thao<br>7. phap-luat<br>8. giao-duc<br>9. suc-khoe<br>10. doi-song | 0. xa-hoi<br>1. the-gioi<br>2. kinh-doanh<br>3. bat-dong-san<br>4. the-thao<br>5. lao-dong-viec-lam<br>6. tam-long-nhan-ai<br>7. suc-khoe<br>8. van-hoa<br>9. giai-tri<br>10. suc-manh-so<br>11. giao-duc<br>12. an-sinh<br>13. phap-luat | 0. thoi-su<br>1. kinh-doanh<br>2. the-thao<br>3. van-hoa<br>4. giai-tri<br>5. the-gioi<br>6. doi-song<br>7. giao-duc<br>8. suc-khoe<br>9. thong-tin-truyen-thong<br>10. phap-luat<br>11. oto-xe-may<br>12. bat-dong-san<br>13. du-lich |

**🌟 Subcategory Support:**
You can also crawl specific subcategories by using the format `category/subcategory`:
- `"the-gioi/quan-su"` - Military news under World category
- `"kinh-doanh/doanh-nghiep"` - Business/Enterprise news

**Example URLs:**
- VNExpress: `https://vnexpress.net/the-gioi/quan-su`
- DanTri: `https://dantri.com.vn/the-gioi/quan-su.htm`
- VietnamNet: `https://vietnamnet.vn/the-gioi/quan-su`


For example if you set configuration file like this:  
```yaml
# if task == "type"
article_type: "khoa-hoc"
total_pages: 3
```  
It will crawl articles from
```
https://vnexpress.net/khoa-hoc-p1
https://vnexpress.net/khoa-hoc-p2
https://vnexpress.net/khoa-hoc-p3
```
🌟 **To crawl article in all of available categories, you just need to set  `article_type: "all"`.**

```yaml
# if task == "type"
article_type: "all"
total_pages: 3
```  

## 🚀 Crawling faster with MultiThreading

By increasing the value of `num_workers`, you can accelerate the crawling process by utilizing multiple threads simultaneously. ⚠️ However, it's important to note that setting `num_workers` too high may result in receiving a "Too Many Requests" error from the news website, preventing any further URL crawling.

## ✔️  Todo
- [x] Speed up crawling progress with multithreading
- [x] Add logging module
- [x] Use yml config file instead of argparse
- [x] Crawl in other news websites
