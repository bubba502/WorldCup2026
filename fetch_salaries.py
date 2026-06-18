#!/usr/bin/env python3
"""
Scrape Capology.com for World Cup 2026 player salary estimates.
Fetches WC rosters from ESPN, maps club names → Capology URLs,
matches players by name, converts weekly wages to annual ~$XM format.

Usage: python fetch_salaries.py
Output: salary_capology.json
"""

from __future__ import annotations

import json
import re
import time
import unicodedata
import urllib.request
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup

ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer"
CAPOLOGY_BASE = "https://www.capology.com/club"
OUT_PATH = "C:/Users/tobri/AIAgency/clients/worldcup/salary_capology.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

# Club display name (as ESPN reports it) → Capology URL slug
CLUB_SLUGS = {
    # Premier League
    "Arsenal": "arsenal",
    "Aston Villa": "aston-villa",
    "Brentford": "brentford",
    "Brighton & Hove Albion": "brighton-hove-albion",
    "Burnley FC": "burnley",
    "Chelsea": "chelsea",
    "Crystal Palace": "crystal-palace",
    "Everton": "everton",
    "Fulham FC": "fulham",
    "Leicester City": "leicester-city",
    "Liverpool": "liverpool",
    "Manchester City": "manchester-city",
    "Manchester United": "manchester-united",
    "Newcastle United": "newcastle-united",
    "Nottingham Forest": "nottingham-forest",
    "Tottenham Hotspur": "tottenham-hotspur",
    "West Ham United": "west-ham-united",
    "Wolverhampton Wanderers": "wolverhampton",
    # La Liga
    "Athletic Bilbao": "athletic-bilbao",
    "Atletico Madrid": "atletico-madrid",
    "CA Osasuna": "osasuna",
    "FC Barcelona": "barcelona",
    "Girona FC": "girona",
    "Getafe CF": "getafe",
    "Rayo Vallecano": "rayo-vallecano",
    "RC Celta": "celta-vigo",
    "Real Betis": "real-betis",
    "Real Madrid": "real-madrid",
    "Real Sociedad": "real-sociedad",
    "Sevilla FC": "sevilla",
    "Valencia CF": "valencia",
    "Villarreal CF": "villarreal",
    # Bundesliga
    "1. FC Heidenheim 1846": "fc-heidenheim",
    "1. FC Union Berlin": "union-berlin",
    "1. FSV Mainz 05": "mainz-05",
    "Bayer Leverkusen": "bayer-leverkusen",
    "Borussia Dortmund": "borussia-dortmund",
    "Borussia Monchengladbach": "borussia-monchengladbach",
    "Eintracht Frankfurt": "eintracht-frankfurt",
    "FC Augsburg": "fc-augsburg",
    "FC Bayern Munich": "bayern-munich",
    "Bayern Munich": "bayern-munich",
    "RB Leipzig": "rb-leipzig",
    "SC Freiburg": "sc-freiburg",
    "TSG Hoffenheim": "tsg-hoffenheim",
    "VfB Stuttgart": "vfb-stuttgart",
    "VfL Bochum": "vfl-bochum",
    "VfL Wolfsburg": "vfl-wolfsburg",
    "Werder Bremen": "werder-bremen",
    # Serie A
    "AC Milan": "ac-milan",
    "ACF Fiorentina": "fiorentina",
    "AS Roma": "as-roma",
    "Atalanta": "atalanta",
    "Bologna FC": "bologna",
    "Cagliari": "cagliari",
    "Empoli": "empoli",
    "Genoa CFC": "genoa",
    "Hellas Verona": "hellas-verona",
    "Inter Milan": "inter-milan",
    "Juventus": "juventus",
    "Lazio": "ss-lazio",
    "SS Lazio": "ss-lazio",
    "Monza": "monza",
    "Napoli": "napoli",
    "SSC Napoli": "napoli",
    "Salernitana": "salernitana",
    "Sassuolo": "sassuolo",
    "Torino FC": "torino",
    "Udinese": "udinese",
    # Ligue 1
    "AS Monaco": "as-monaco",
    "FC Lorient": "lorient",
    "FC Nantes": "nantes",
    "Lille OSC": "lille",
    "Montpellier HSC": "montpellier",
    "Nice": "nice",
    "OGC Nice": "nice",
    "Olympique de Marseille": "marseille",
    "Olympique Lyonnais": "olympique-lyonnais",
    "Paris Saint-Germain": "paris-saint-germain",
    "RC Lens": "rc-lens",
    "RC Strasbourg": "rc-strasbourg",
    "Rennes": "rennes",
    "Stade Brestois 29": "brest",
    "Stade de Reims": "reims",
    "Stade Rennais FC": "rennes",
    "Toulouse FC": "toulouse",
    # Primeira Liga
    "FC Porto": "fc-porto",
    "Porto": "fc-porto",
    "SL Benfica": "sl-benfica",
    "Sporting CP": "sporting-cp",
    "SC Braga": "sc-braga",
    "Vitória SC": "vitoria-guimaraes",
    # Eredivisie
    "AFC Ajax": "ajax",
    "Ajax": "ajax",
    "AZ Alkmaar": "az-alkmaar",
    "FC Twente": "fc-twente",
    "Feyenoord": "feyenoord",
    "Feyenoord Rotterdam": "feyenoord",
    "NEC Nijmegen": "nec-nijmegen",
    "PSV Eindhoven": "psv-eindhoven",
    # Belgian Pro League
    "Anderlecht": "anderlecht",
    "Club Brugge": "club-brugge",
    "Club Brugge KV": "club-brugge",
    "KAA Gent": "kaa-gent",
    "KRC Genk": "krc-genk",
    "Royal Antwerp FC": "royal-antwerp",
    "Union Saint-Gilloise": "union-saint-gilloise",
    # Scottish
    "Celtic FC": "celtic",
    "Rangers FC": "rangers",
    "Heart of Midlothian": "hearts",
    # MLS
    "Atlanta United FC": "atlanta-united",
    "Charlotte FC": "charlotte",
    "Chicago Fire FC": "chicago-fire",
    "Colorado Rapids": "colorado-rapids",
    "Columbus Crew": "columbus-crew",
    "FC Cincinnati": "fc-cincinnati",
    "FC Dallas": "fc-dallas",
    "Houston Dynamo FC": "houston-dynamo",
    "Inter Miami CF": "inter-miami",
    "LA Galaxy": "la-galaxy",
    "LAFC": "los-angeles-fc",
    "Minnesota United FC": "minnesota-united",
    "Nashville SC": "nashville-sc",
    "New England Revolution": "new-england-revolution",
    "New York City FC": "new-york-city",
    "New York Red Bulls": "new-york-red-bulls",
    "Orlando City SC": "orlando-city",
    "Philadelphia Union": "philadelphia-union",
    "Portland Timbers": "portland-timbers",
    "Real Salt Lake": "real-salt-lake",
    "San Jose Earthquakes": "san-jose-earthquakes",
    "Seattle Sounders FC": "seattle-sounders",
    "Sporting Kansas City": "sporting-kansas-city",
    "St. Louis City SC": "st-louis-city",
    "Toronto FC": "toronto",
    "Vancouver Whitecaps FC": "vancouver-whitecaps",
    # Saudi Pro League
    "Al Ahli": "al-ahli",
    "Al Fateh": "al-fateh",
    "Al Hilal": "al-hilal",
    "Al Ittihad": "al-ittihad",
    "Al Nassr": "al-nassr",
    "Al Qadsiah": "al-qadsiah",
    "Al Shabab": "al-shabab",
    "Al-Ain": "al-ain",
    # Other
    "Boca Juniors": "boca-juniors",
    "River Plate": "river-plate",
    "Flamengo": "flamengo",
    "Palmeiras": "palmeiras",
    "São Paulo FC": "sao-paulo",
    "Fluminense": "fluminense",
    "Internacional": "internacional",
    "Atletico Mineiro": "atletico-mineiro",
    "Botafogo": "botafogo",
    "Galatasaray": "galatasaray",
    "Fenerbahce": "fenerbahce",
    "Besiktas JK": "besiktas",
    "Trabzonspor": "trabzonspor",
}


# ── Name normalization ────────────────────────────────────────────────────────

def normalize(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_str = nfkd.encode("ascii", "ignore").decode("ascii")
    lower = ascii_str.lower()
    lower = re.sub(r"\b(jr|sr|ii|iii|iv)\.?\b", "", lower)
    lower = re.sub(r"[^a-z\s'-]", "", lower)
    return re.sub(r"\s+", " ", lower).strip()


def last_name(norm: str) -> str:
    parts = norm.split()
    return parts[-1] if parts else norm


# ── ESPN roster fetch ─────────────────────────────────────────────────────────

def fetch_json_espn(url: str):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except Exception:
        return None


def get_all_wc_teams() -> list[dict]:
    d = fetch_json_espn(f"{ESPN_BASE}/FIFA.WORLD/teams?limit=100")
    if not d:
        return []
    raw = (d.get("sports") or [{}])[0].get("leagues", [{}])[0].get("teams", []) or d.get("teams", [])
    teams = []
    for t in raw:
        tm = t.get("team") or t
        if tm.get("id") and tm.get("displayName"):
            teams.append({"id": str(tm["id"]), "name": tm["displayName"]})
    return sorted(teams, key=lambda x: x["name"])


def build_player_index(teams: list[dict]) -> tuple[dict, dict]:
    """
    Returns:
      id_to_club:    {espn_id: club_name}
      name_to_ids:   {normalized_full_name: [espn_id, ...]}
    """
    id_to_club: dict[str, str] = {}
    name_to_ids: dict[str, list[str]] = defaultdict(list)

    for t in teams:
        d = fetch_json_espn(f"{ESPN_BASE}/FIFA.WORLD/teams/{t['id']}/roster")
        if not d:
            continue
        athletes = d.get("athletes", [])
        for a in athletes:
            aid = str(a.get("id", ""))
            if not aid:
                continue
            full = a.get("fullName") or a.get("displayName") or ""
            norm = normalize(full)
            if norm:
                name_to_ids[norm].append(aid)
        time.sleep(0.15)

    return id_to_club, name_to_ids


# ── Capology scraping ─────────────────────────────────────────────────────────

def parse_weekly_wage(text: str) -> int | None:
    """Parse '$600,000' or '€600,000' or '£600,000' → int."""
    clean = re.sub(r"[^\d]", "", text)
    return int(clean) if clean else None


def annual_to_display(annual: int) -> str:
    m = annual / 1_000_000
    if m >= 1:
        return f"~${m:.1f}M"
    k = annual / 1_000
    return f"~${k:.0f}K"


def scrape_club_salaries(slug: str) -> list[dict]:
    """
    Returns list of {name, annual_usd} for a club.
    Capology embeds data as inline JS: var data = [{...}]
    with accounting.formatMoney("19532340", ...) calls.
    """
    url = f"{CAPOLOGY_BASE}/{slug}/salaries/"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code == 429:
            print(f"    429 rate-limited on {slug}, backing off 10s")
            time.sleep(10)
            resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code != 200:
            print(f"    HTTP {resp.status_code} for {slug}")
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        rows = []

        for script in soup.find_all("script"):
            txt = script.string or ""
            if "var data = [" not in txt:
                continue
            # Each player block starts with {'name': "..."
            # Extract name from the HTML anchor text
            # Extract annual_gross_usd from accounting.formatMoney("DIGITS", "$ ", 0)
            # Use split on },{  to get individual player blocks
            idx_start = txt.index("var data = [") + len("var data = [")
            # Find matching ]
            depth, idx_end = 0, idx_start
            for i, ch in enumerate(txt[idx_start:], idx_start):
                if ch == "[":
                    depth += 1
                elif ch == "]":
                    if depth == 0:
                        idx_end = i
                        break
                    depth -= 1
            block = txt[idx_start:idx_end]

            # Split on player boundaries — each object starts with {'name':
            player_blocks = re.split(r"\},\s*\{", block)
            for pb in player_blocks:
                # Extract display name from anchor tag text (last text node before </a>)
                name_m = re.search(r">([^<>]+)</a>", pb)
                if not name_m:
                    continue
                player_name = name_m.group(1).strip()
                if not player_name or player_name.startswith("<"):
                    continue
                # Extract annual gross USD — raw integer inside formatMoney("DIGITS", "$ "
                usd_m = re.search(r"annual_gross_usd.*?formatMoney\(\"(\d+)\"", pb)
                if not usd_m:
                    continue
                annual_usd = int(usd_m.group(1))
                if annual_usd > 0:
                    rows.append({"name": player_name, "annual": annual_usd})
            break  # only one data block per page

        return rows
    except Exception as e:
        print(f"    Error scraping {slug}: {e}")
        return []


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("Step 1: Fetching WC 2026 teams from ESPN...")
    teams = get_all_wc_teams()
    print(f"  Found {len(teams)} teams")

    print("\nStep 2: Building player name -> ESPN ID index (fetching 48 rosters)...")
    _, name_to_ids = build_player_index(teams)
    # Also build last_name → list of (norm_full, id) for fallback matching
    last_to_entries: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for norm, ids in name_to_ids.items():
        for aid in ids:
            last_to_entries[last_name(norm)].append((norm, aid))
    print(f"  Indexed {sum(len(v) for v in name_to_ids.values())} players")

    print("\nStep 3: Scraping Capology club salary pages...")
    salary_out: dict[str, str] = {}   # espn_id → display string
    matched = 0
    skipped_ambiguous = 0
    skipped_no_match = 0

    unique_slugs = sorted(set(CLUB_SLUGS.values()))
    for i, slug in enumerate(unique_slugs):
        print(f"  [{i+1}/{len(unique_slugs)}] {slug}...", end=" ", flush=True)
        rows = scrape_club_salaries(slug)
        print(f"{len(rows)} players found")

        for row in rows:
            norm = normalize(row["name"])
            ids = name_to_ids.get(norm)
            if ids and len(ids) == 1:
                salary_out[ids[0]] = annual_to_display(row["annual"])
                matched += 1
                continue
            # Fallback: last-name match
            ln = last_name(norm)
            candidates = last_to_entries.get(ln, [])
            if len(candidates) == 1:
                salary_out[candidates[0][1]] = annual_to_display(row["annual"])
                matched += 1
            elif len(candidates) > 1:
                skipped_ambiguous += 1
            else:
                skipped_no_match += 1

        time.sleep(2.0)  # respectful rate limiting — Capology 429s at ~1s

    print(f"\nResults: {matched} matched | {skipped_ambiguous} ambiguous | {skipped_no_match} no match")

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(salary_out, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(salary_out)} salaries to {OUT_PATH}")


if __name__ == "__main__":
    main()
