"""
Công cụ tìm kiếm tin tức tiếng Việt
"""

from elastic_indexer import ElasticIndexer


def print_article(article, index):
    """In thông tin bài báo"""
    score = article.get('score', 0)

    print(f"\n{'=' * 80}")
    print(f"[{index}] {article['title']}")
    print(f"{'=' * 80}")
    print(f"Diem: {score:.2f}")

    # Hiển thị lý do rank cao
    matched_title = article.get('matched_in_title', [])
    matched_body = article.get('matched_in_body', [])

    if matched_title or matched_body:
        print(f"\nLy do duoc chon:")
        if matched_title:
            clean_title = matched_title[0].replace('<mark>', '[').replace('</mark>', ']')
            print(f"  Tieu de: {clean_title}")
        if matched_body:
            print(f"  Noi dung:")
            for fragment in matched_body[:2]:
                clean_fragment = fragment.replace('<mark>', '[').replace('</mark>', ']')
                print(f"    - {clean_fragment}...")

    print(f"\nNguon: {article.get('source', 'N/A')}")
    print(f"Chuyen muc: {article.get('category', 'N/A')}")
    print(f"Ngay: {article.get('publish_date_str', 'N/A')}")
    print(f"Link: {article.get('url', 'N/A')}")
    print(f"\nNoi dung:")
    body = article.get('body', '')
    preview = body[:250] + "..." if len(body) > 250 else body
    print(preview)


def main():
    """Hàm tìm kiếm chính"""
    print("=" * 80)
    print("TÌM KIẾM TIN TỨC CHIẾN TRANH")
    print("=" * 80)

    try:
        indexer = ElasticIndexer(
            es_url="http://localhost:9200",
            index_name="news_quansu"
        )
        print("Đã kết nối Elasticsearch")
    except Exception as e:
        print(f"Lỗi kết nối: {e}")
        return

    while True:
        print("\n" + "=" * 80)
        query = input("Nhập từ khóa (hoặc 'thoat' để kết thúc): ").strip()
        if query.lower() in ['thoat', 'quit', 'exit', 'q']:

            break

        if not query:
            print("Vui lòng nhập từ khóa")
            continue

        try:
            results = indexer.search(query, size=10)

            if not results:
                print("\nKhông tìm thấy bài báo nào")
                continue

            print(f"\nTìm thấy {len(results)} bài báo:")

            for i, article in enumerate(results, 1):
                print_article(article, i)

            print("\n" + "=" * 80)

        except Exception as e:
            print(f"Lỗi tìm kiếm: {e}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Goodbye!")
    except Exception as e:
        print(f"\nError: {e}")

