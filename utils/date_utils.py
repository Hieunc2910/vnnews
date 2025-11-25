"""
Utility functions for parsing and comparing dates from Vietnamese news websites
"""
import re
from datetime import datetime, timedelta


def parse_vnexpress_date(date_str):
    """
    Parse VNExpress date format
    Examples: "Thứ hai, 25/11/2025, 10:30 (GMT+7)"
    """
    try:
        # Extract date part: DD/MM/YYYY
        match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', date_str)
        if match:
            day, month, year = match.groups()
            return datetime(int(year), int(month), int(day))
    except:
        pass
    return None


def parse_dantri_date(date_str):
    """
    Parse Dân Trí date format
    Examples: "25/11/2025 10:30", "Thứ hai, 25/11/2025, 10:30"
    """
    try:
        # Extract date part: DD/MM/YYYY
        match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', date_str)
        if match:
            day, month, year = match.groups()
            return datetime(int(year), int(month), int(day))
    except:
        pass
    return None


def parse_vietnamnet_date(date_str):
    """
    Parse VietnamNet date format
    Examples: "25/11/2025, 10:30 (GMT+7)", "Thứ hai, 25/11/2025"
    """
    try:
        # Extract date part: DD/MM/YYYY
        match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', date_str)
        if match:
            day, month, year = match.groups()
            return datetime(int(year), int(month), int(day))
    except:
        pass
    return None


def is_recent_article(date_str, max_days_old, parse_func):
    """
    Check if an article is recent enough based on its date string

    Args:
        date_str: Date string from the article
        max_days_old: Maximum age in days
        parse_func: Function to parse the date string

    Returns:
        True if article is recent enough, False otherwise
    """
    if not date_str or date_str == "N/A":
        # If we can't determine the date, assume it's recent to avoid skipping
        return True

    article_date = parse_func(date_str)
    if not article_date:
        return True  # If parsing fails, don't skip

    current_date = datetime.now()
    age_days = (current_date - article_date).days

    return age_days <= max_days_old


def get_days_old(date_str, parse_func):
    """
    Get the age of an article in days

    Args:
        date_str: Date string from the article
        parse_func: Function to parse the date string

    Returns:
        Number of days old, or None if date cannot be parsed
    """
    if not date_str or date_str == "N/A":
        return None

    article_date = parse_func(date_str)
    if not article_date:
        return None

    current_date = datetime.now()
    return (current_date - article_date).days

