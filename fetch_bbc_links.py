#!/usr/bin/env python3
"""
Fetch BBC Sport match recap links for completed World Cup games.
Matches BBC Sport World Cup RSS feed articles to ESPN event IDs by team names.
Saves results to bbc_links.json keyed by ESPN event ID.

Scheduled via Windows Task Scheduler at 00:00, 03:00, 06:00, 09:00 ET.
"""
from __future__ import annotations

import json
import re
import subprocess
import time
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

BBC_RSS    = "https://feeds.bbci.co.uk/sport/football/world-cup/rss.xml"
DDG_LITE   = "https://lite.duckduckgo.com/lite/"
ESPN_BASE  = "https://site.api.espn.com/apis/site/v2/sports/soccer"
OUT_PATH   = Path("C:/Users/tobri/AIAgency/clients/worldcup/bbc_links.json")
LOG_PATH   = Path("C:/Users/tobri/AIAgency/clients/worldcup/bbc_links_log.txt")

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def log(msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def normalize(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_str = nfkd.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_str.lower().strip())


def fetch(url: str, timeout: int = 20) -> Optional[bytes]:
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception as e:
        log(f"  fetch error {url}: {e}")
        return None


def get_completed_wc_games() -> List[Dict]:
    """Return completed WC games from ESPN scoreboard (both halves of tournament)."""
    games = []
    ranges = ["20260611-20260630", "20260701-20260726"]
    for date_range in ranges:
        data = fetch(f"{ESPN_BASE}/FIFA.WORLD/scoreboard?dates={date_range}&limit=200")
        if not data:
            continue
        d = json.loads(data)
        for ev in d.get("events", []):
            comp = (ev.get("competitions") or [{}])[0]
            status = comp.get("status", {}).get("type", {}).get("completed", False)
            if not status:
                continue
            competitors = comp.get("competitors", [])
            if len(competitors) != 2:
                continue
            home = competitors[0].get("team", {}).get("displayName", "")
            away = competitors[1].get("team", {}).get("displayName", "")
            games.append({
                "id": str(ev["id"]),
                "home": home,
                "away": away,
                "home_norm": normalize(home),
                "away_norm": normalize(away),
                "date": ev.get("date", ""),
            })
    return games


def fetch_bbc_articles() -> List[Dict]:
    """Parse BBC Sport World Cup RSS feed into list of {title, link, pub_date}."""
    data = fetch(BBC_RSS)
    if not data:
        return []
    try:
        root = ET.fromstring(data)
    except ET.ParseError as e:
        log(f"  RSS parse error: {e}")
        return []

    articles = []
    channel = root.find("channel")
    if channel is None:
        return []
    for item in channel.findall("item"):
        title = (item.findtext("title") or "").strip()
        link  = (item.findtext("link") or "").strip()
        pub   = (item.findtext("pubDate") or "").strip()
        if title and link:
            articles.append({"title": title, "link": link, "pub_date": pub})
    return articles


# BBC uses different names for some nations — map ESPN display name → BBC variants
BBC_ALIASES: Dict[str, List[str]] = {
    "congo dr":          ["dr congo", "democratic republic of congo", "congo"],
    "united states":     ["usa", "united states"],
    "south korea":       ["korea republic", "korea"],
    "ivory coast":       ["cote d'ivoire", "ivory coast"],
    "cape verde":        ["cape verde islands"],
    "bosnia-herz.":      ["bosnia", "bosnia and herzegovina"],
    "czechia":           ["czech republic"],
    "curacao":           ["curacao"],
}


def name_tokens(norm: str) -> List[str]:
    """Return the normalized name plus any BBC alias variants."""
    tokens = [norm]
    for key, aliases in BBC_ALIASES.items():
        if key in norm:
            tokens.extend(aliases)
    return tokens


def match_article_to_game(article: Dict, games: List[Dict]) -> Optional[str]:
    """
    Try to match a BBC article title to an ESPN game.
    BBC titles typically: "France 2-1 Argentina: Mbappe scores..."
    Returns ESPN event ID if matched, else None.
    """
    title_norm = normalize(article["title"])
    for game in games:
        for home in name_tokens(game["home_norm"]):
            for away in name_tokens(game["away_norm"]):
                if home in title_norm and away in title_norm:
                    return game["id"]
                # First-word fallback for long compound names
                h1, a1 = home.split()[0], away.split()[0]
                if len(h1) > 3 and len(a1) > 3 and h1 in title_norm and a1 in title_norm:
                    return game["id"]
    return None


def bbc_name(espn_name: str) -> str:
    """Convert ESPN team name to BBC-style name for search queries."""
    mapping = {
        "Congo DR":             "DR Congo",
        "United States":        "USA",
        "Bosnia-Herzegovina":   "Bosnia",
        "Czechia":              "Czech Republic",
        "Ivory Coast":          "Ivory Coast",
        "Cape Verde":           "Cape Verde",
        "Curacao":              "Curacao",
        "Türkiye":              "Turkey",
        "South Korea":          "South Korea",
    }
    return mapping.get(espn_name, espn_name)


def search_bbc_ddg(home: str, away: str) -> Optional[str]:
    """Search DuckDuckGo Lite for BBC Sport match report for this game."""
    h, a = bbc_name(home), bbc_name(away)
    for query in [
        f"site:bbc.com/sport {h} {a} World Cup 2026",
        f"site:bbc.com/sport {h} {a} World Cup",
        f"bbc sport {h} {a} World Cup 2026 match report",
    ]:
        try:
            resp = requests.post(
                DDG_LITE,
                data={"q": query, "kl": "us-en"},
                headers=HEADERS,
                timeout=15,
            )
            soup = BeautifulSoup(resp.text, "lxml")
            for link in soup.find_all("a", href=True):
                href = link["href"]
                if ("bbc.com/sport" in href or "bbc.co.uk/sport" in href) and "/articles/" in href:
                    return href
            for link in soup.find_all("a", href=True):
                href = link["href"]
                if "bbc.com/sport/football" in href or "bbc.co.uk/sport/football" in href:
                    return href
        except Exception as e:
            log(f"    DDG error ({query[:40]}): {e}")
        time.sleep(1.0)
    return None


def main() -> None:
    log("=== fetch_bbc_links starting ===")

    # Load existing links
    existing: Dict[str, str] = {}
    if OUT_PATH.exists():
        try:
            existing = json.loads(OUT_PATH.read_text(encoding="utf-8"))
            log(f"  Loaded {len(existing)} existing links")
        except Exception:
            pass

    log("Fetching completed WC games from ESPN...")
    games = get_completed_wc_games()
    log(f"  {len(games)} completed games")
    if not games:
        log("  No completed games found — exiting")
        return

    # Pass 1: fast RSS match (covers recent games)
    log("Pass 1: BBC Sport RSS...")
    articles = fetch_bbc_articles()
    log(f"  {len(articles)} articles")
    added = 0
    for article in articles:
        event_id = match_article_to_game(article, games)
        if event_id and event_id not in existing:
            existing[event_id] = article["link"]
            log(f"  + RSS: {article['title'][:55]} -> {event_id}")
            added += 1

    # Pass 2: DDG search for any games still missing a link
    missing = [g for g in games if g["id"] not in existing]
    log(f"Pass 2: DDG search for {len(missing)} unmatched games...")
    for g in missing:
        url = search_bbc_ddg(g["home"], g["away"])
        if url:
            existing[g["id"]] = url
            log(f"  + DDG: {g['home']} vs {g['away']} -> {url[:70]}")
            added += 1
        else:
            log(f"  - no result: {g['home']} vs {g['away']}")
        time.sleep(2.0)  # be polite to DDG

    OUT_PATH.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"Done: +{added} new links | total {len(existing)} | saved to {OUT_PATH}")

    if added > 0:
        try:
            repo_dir = str(OUT_PATH.parent)
            subprocess.run(["git", "-C", repo_dir, "add", "bbc_links.json"], check=True)
            subprocess.run(["git", "-C", repo_dir, "commit", "-m", f"chore: update BBC links (+{added} new)"], check=True)
            subprocess.run(["git", "-C", repo_dir, "push"], check=True)
            log(f"  Pushed bbc_links.json to GitHub → Vercel deploying")
        except subprocess.CalledProcessError as e:
            log(f"  Git push failed: {e}")


if __name__ == "__main__":
    main()
