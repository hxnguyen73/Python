from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import requests
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
        end = datetime.now(tz=timezone.utc)
        start = end - timedelta(days=7)

        resp = requests.get(
            "https://data.alpaca.markets/v1beta1/news",
            headers={
                "Apca-Api-Key-Id": api_key,
                "Apca-Api-Secret-Key": secret_key,
            },
            params={
                "symbols": symbol,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "limit": limit,
                "sort": "desc",
            },
            timeout=10,
        )
        resp.raise_for_status()
        articles = resp.json().get("news", [])

        if not articles:
            st.info("No recent news found.")
            return

        for article in articles:
            headline = article.get("headline", "No title")
            url = article.get("url", "#")
            summary = article.get("summary", "")
            created_at = article.get("created_at", "")
            ts = created_at[:16].replace("T", " ") if created_at else ""
            st.markdown(f"**[{headline}]({url})** — {ts}")
            if summary:
                st.caption(summary[:200] + ("…" if len(summary) > 200 else ""))
            st.divider()

    except requests.HTTPError as exc:
        st.error(f"News API error {exc.response.status_code}: {exc.response.text[:200]}")
    except Exception as exc:
        st.error(f"Could not load news: {exc}")
