from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import streamlit as st
from dotenv import load_dotenv

load_dotenv()


def render_news(symbol: str, limit: int = 10) -> None:
    """Render recent news headlines from Alpaca News API."""
    st.subheader(f"News — {symbol}")

    api_key = os.getenv("ALPACA_API_KEY")
    secret_key = os.getenv("ALPACA_SECRET_KEY")

    if not api_key or not secret_key:
        st.warning("Set ALPACA_API_KEY and ALPACA_SECRET_KEY in .env to enable news.")
        return

    try:
        from alpaca.data.historical import StockHistoricalDataClient
        from alpaca.data.requests import NewsRequest

        client = StockHistoricalDataClient(api_key, secret_key)
        end = datetime.now(tz=timezone.utc)
        start = end - timedelta(days=7)

        request = NewsRequest(symbols=[symbol], start=start, end=end, limit=limit)
        news = client.get_news(request)
        articles = news.news if hasattr(news, "news") else []

        if not articles:
            st.info("No recent news found.")
            return

        for article in articles:
            headline = getattr(article, "headline", "No title")
            url = getattr(article, "url", "#")
            summary = getattr(article, "summary", "")
            created = getattr(article, "created_at", None)
            ts = created.strftime("%Y-%m-%d %H:%M") if created else ""
            st.markdown(f"**[{headline}]({url})** — {ts}")
            if summary:
                st.caption(summary[:200] + ("…" if len(summary) > 200 else ""))
            st.divider()

    except Exception as exc:
        st.error(f"Could not load news: {exc}")
