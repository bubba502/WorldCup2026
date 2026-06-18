#!/usr/bin/env python3
"""
Fallback salary fetch: looks up individual Capology player pages
for WC players not covered by the club-scraping pass.

Uses Capology's search_players.json to find player URLs, then
extracts USD annual salary from each player page.

Usage: python fetch_salaries_fallback.py
Updates salary_capology.json in-place.
"""

from __future__ import annotations

import json
import re
import time
import unicodedata
import urllib.request
from typing import Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup

ESPN_BASE  = "https://site.api.espn.com/apis/site/v2/sports/soccer"
CAPOLOGY   = "https://www.capology.com"
JSON_PATH  = "C:/Users/tobri/AIAgency/clients/worldcup/salary_capology.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.capology.com/",
}


def normalize(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_str = nfkd.encode("ascii", "ignore").decode("ascii")
    lower = ascii_str.lower()
    lower = re.sub(r"\b(jr|sr|ii|iii|iv)\.?\b", "", lower)
    lower = re.sub(r"[^a-z\s'-]", "", lower)
    return re.sub(r"\s+", " ", lower).strip()


def fetch_espn(url: str):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except Exception:
        return None


def get_wc_players() -> List[dict]:
    """Returns [{id, name}] for all 736 WC players."""
    d = fetch_espn(f"{ESPN_BASE}/FIFA.WORLD/teams?limit=100")
    if not d:
        return []
    raw = (d.get("sports") or [{}])[0].get("leagues", [{}])[0].get("teams", []) or d.get("teams", [])
    teams = [{"id": str((t.get("team") or t)["id"])} for t in raw if (t.get("team") or t).get("id")]
    players = []
    for t in teams:
        r = fetch_espn(f"{ESPN_BASE}/FIFA.WORLD/teams/{t['id']}/roster")
        if not r:
            continue
        for a in r.get("athletes", []):
            aid = str(a.get("id", ""))
            name = a.get("fullName") or a.get("displayName") or ""
            if aid and name:
                players.append({"id": aid, "name": name})
        time.sleep(0.15)
    return players


def build_capology_index() -> Dict[str, str]:
    """Returns {normalized_name: capology_link} from search_players.json."""
    r = requests.get(f"{CAPOLOGY}/static/files/search_players.json", headers=HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()
    return {normalize(entry["name"]): entry["link"] for entry in data if entry.get("name") and entry.get("link")}


def fetch_player_salary_usd(link: str) -> Optional[int]:
    """Fetch Capology player page and return annual gross USD integer."""
    url = f"{CAPOLOGY}{link}/"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code == 429:
            time.sleep(10)
            resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code != 200:
            return None
        # Pattern: annual-fixed...formatMoney("DIGITS", "$ ", 0)
        m = re.search(r"annual-fixed.*?formatMoney\(\"(\d+)\",\s*\"\$\s*\"", resp.text, re.DOTALL)
        if m:
            val = int(m.group(1))
            return val if val > 0 else None
        return None
    except Exception:
        return None


def annual_to_display(annual: int) -> str:
    m = annual / 1_000_000
    if m >= 1:
        return f"~${m:.1f}M"
    k = annual / 1_000
    return f"~${k:.0f}K"


def main():
    # Load existing salary data
    with open(JSON_PATH, encoding="utf-8") as f:
        salary_data: dict[str, str] = json.load(f)
    print(f"Existing salary entries: {len(salary_data)}")

    print("Fetching WC player roster from ESPN...")
    players = get_wc_players()
    print(f"  {len(players)} players")

    unmatched = [p for p in players if p["id"] not in salary_data]
    print(f"  {len(unmatched)} without salary data")

    print("Loading Capology search index...")
    cap_index = build_capology_index()
    print(f"  {len(cap_index)} players indexed")

    # Match unmatched players to Capology links
    to_fetch: List[Tuple[str, str, str]] = []  # (espn_id, player_name, capology_link)
    no_match = []
    for p in unmatched:
        norm = normalize(p["name"])
        link = cap_index.get(norm)
        if link:
            to_fetch.append((p["id"], p["name"], link))
        else:
            no_match.append(p["name"])

    print(f"  {len(to_fetch)} matched in Capology index")
    print(f"  {len(no_match)} not found (likely lower-league players)")

    print(f"\nFetching {len(to_fetch)} individual player pages...")
    added = 0
    failed = 0
    for i, (espn_id, name, link) in enumerate(to_fetch):
        annual = fetch_player_salary_usd(link)
        if annual:
            salary_data[espn_id] = annual_to_display(annual)
            added += 1
            if (i + 1) % 10 == 0:
                print(f"  [{i+1}/{len(to_fetch)}] {added} added so far...")
        else:
            failed += 1
        time.sleep(1.5)

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(salary_data, f, indent=2, ensure_ascii=False)

    print(f"\nDone: +{added} added | {failed} no salary data | total {len(salary_data)}")
    print(f"Not in Capology index ({len(no_match)} players):")
    for n in sorted(no_match)[:20]:
        print(f"  {n}")


if __name__ == "__main__":
    main()
