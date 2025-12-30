from datetime import datetime, timedelta


def parse_qdnd_date(date_str):
    """
    Parse QDND date format: 2025-05-27T06:31:00+07:00
    Trả về datetime object
    """
    try:
        # Loại bỏ timezone (+07:00) vì datetime.strptime không xử lý được
        if '+' in date_str:
            date_str = date_str.split('+')[0]
        elif 'Z' in date_str:
            date_str = date_str.replace('Z', '')

        return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S")
    except:
        return None


def parse_dantri_date(date_str):
    """Parse DanTri date format"""
    try:
        return datetime.strptime(date_str, "%d/%m/%Y %H:%M %Z")
    except:
        try:
            return datetime.strptime(date_str, "%d/%m/%Y")
        except:
            return None


def parse_vietnamnet_date(date_str):
    """Parse VietnamNet date format"""
    try:
        return datetime.strptime(date_str, "%d/%m/%Y %H:%M")
    except:
        return None


def parse_vnexpress_date(date_str):
    """Parse VNExpress date format"""
    try:
        # Format: "Thứ ba, 30/12/2025, 14:30 (GMT+7)"
        date_str = date_str.split(',')[-2].strip()  # Lấy phần "30/12/2025"
        return datetime.strptime(date_str, "%d/%m/%Y")
    except:
        return None


def is_recent_article(date_str, max_days_old, parse_func):
    """
    Kiểm tra xem bài viết có trong khoảng max_days_old ngày không
    """
    article_date = parse_func(date_str)
    if not article_date:
        return True  # Nếu không parse được, coi như là mới

    days_old = (datetime.now() - article_date).days
    return days_old <= max_days_old


def get_days_old(date_str, parse_func):
    """Tính số ngày từ ngày xuất bản đến hiện tại"""
    article_date = parse_func(date_str)
    if not article_date:
        return None
    return (datetime.now() - article_date).days