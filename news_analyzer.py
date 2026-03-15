"""
Thu thập và phân tích tin tức: chính trị, kinh tế, crypto.
Có thể dùng RSS, API tin tức (nếu có key), hoặc scrape.
"""
import os
import re
from datetime import datetime, timedelta
from typing import List, Optional
import requests
from loguru import logger

try:
    import feedparser
except ImportError:
    feedparser = None

from config import NEWS_API_KEY, CRYPTO_NEWS_API_KEY


# RSS feeds: crypto, kinh tế, chính trị (Fed, lãi suất, regulation)
CRYPTO_RSS_FEEDS = [
    "https://cointelegraph.com/rss",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://cryptonews.com/news/feed/",
    "https://bitcoinmagazine.com/.rss/full/",
    "https://decrypt.co/feed",
    "https://www.theblock.co/rss.xml",
]
ECONOMY_RSS = [
    "https://feeds.bloomberg.com/markets/news.rss",
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "https://feeds.content.dowjones.io/public/rss/top",
]


def fetch_rss_feeds(urls: List[str], max_items: int = 20) -> List[dict]:
    """Lấy tin từ RSS."""
    articles = []
    if not feedparser:
        return articles
    for url in urls:
        try:
            feed = feedparser.parse(url)
            for e in feed.entries[:max_items]:
                articles.append({
                    "title": e.get("title", ""),
                    "link": e.get("link", ""),
                    "summary": e.get("summary", "")[:500] if e.get("summary") else "",
                    "published": e.get("published", ""),
                    "source": feed.feed.get("title", url),
                })
        except Exception as ex:
            logger.warning(f"RSS {url}: {ex}")
    return articles


def simple_sentiment(text: str) -> float:
    """
    Sentiment đơn giản theo từ khóa (-1 đến 1).
    Bao gồm: crypto, kinh tế, chính trị (Fed, ETF, regulation).
    """
    text_lower = (text or "").lower()
    positive = [
        "bull", "surge", "rally", "growth", "adopt", "approve", "breakout",
        "all-time high", "etf approval", "institutional", "halving", "rate cut",
    ]
    negative = [
        "bear", "crash", "dump", "ban", "sec", "fraud", "hack", "collapse",
        "fear", "lawsuit", "crackdown", "rate hike", "recession",
    ]
    pos = sum(1 for w in positive if w in text_lower)
    neg = sum(1 for w in negative if w in text_lower)
    total = pos + neg
    if total == 0:
        return 0.0
    return (pos - neg) / total


def fetch_news_api(query: str, api_key: str, max_items: int = 10) -> List[dict]:
    """Gọi NewsAPI (cần key tại newsapi.org)."""
    if not api_key:
        return []
    try:
        url = "https://newsapi.org/v2/everything"
        r = requests.get(
            url,
            params={"q": query, "apiKey": api_key, "pageSize": max_items, "language": "en"},
            timeout=10,
        )
        if r.status_code != 200:
            return []
        data = r.json()
        articles = []
        for a in data.get("articles", [])[:max_items]:
            articles.append({
                "title": a.get("title", ""),
                "description": a.get("description", "") or "",
                "url": a.get("url", ""),
                "publishedAt": a.get("publishedAt", ""),
                "source": a.get("source", {}).get("name", ""),
            })
        return articles
    except Exception as e:
        logger.warning(f"NewsAPI: {e}")
        return []


class NewsAnalyzer:
    def __init__(self):
        self.news_api_key = NEWS_API_KEY
        self.crypto_news_key = CRYPTO_NEWS_API_KEY

    def get_crypto_news(self, limit: int = 30) -> List[dict]:
        """Tin crypto từ RSS (và API nếu có)."""
        items = fetch_rss_feeds(CRYPTO_RSS_FEEDS, max_items=limit)
        if self.news_api_key:
            items += fetch_news_api("crypto bitcoin ethereum", self.news_api_key, max_items=10)
        return items

    def get_economy_news(self, limit: int = 15) -> List[dict]:
        """Tin kinh tế, lãi suất, Fed."""
        return fetch_rss_feeds(ECONOMY_RSS, max_items=limit)

    def get_market_sentiment(self) -> dict:
        """
        Tổng hợp sentiment từ tin tức.
        Returns: { "score": -1..1, "crypto_news": [...], "economy_news": [...] }
        """
        crypto = self.get_crypto_news(20)
        economy = self.get_economy_news(10)
        scores = []
        for item in crypto + economy:
            text = (item.get("title") or "") + " " + (item.get("summary") or item.get("description", ""))
            scores.append(simple_sentiment(text))
        avg = sum(scores) / len(scores) if scores else 0.0
        return {
            "score": max(-1, min(1, avg)),
            "crypto_news": crypto[:10],
            "economy_news": economy[:5],
        }

    def get_latest_trends_summary(self) -> str:
        """
        Tóm tắt xu hướng tin tức mới nhất (crypto + kinh tế).
        Dùng để AI tham chiếu khi ra quyết định.
        """
        data = self.get_market_sentiment()
        score = data["score"]
        trend = "bullish" if score > 0.2 else ("bearish" if score < -0.2 else "neutral")
        headlines = []
        for item in (data.get("crypto_news") or [])[:3]:
            headlines.append((item.get("title") or "")[:80])
        for item in (data.get("economy_news") or [])[:2]:
            headlines.append((item.get("title") or "")[:80])
        lines = [f"Sentiment: {trend} (score={score:.2f})"]
        if headlines:
            lines.append("Headlines: " + " | ".join(headlines))
        return "\n".join(lines)
