#!/usr/bin/env python3
"""
Generate complete PLAYER_DATA + LEAGUE_DATA for all 48 WC 2026 teams.
Fetches from ESPN's public API. Outputs a JS const block to paste into index.html.

Usage: python generate_player_data.py
Output: player_data_generated.js
"""

import json
import re
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer"

LEAGUE_NAMES = {
    'eng.1': 'Premier League', 'esp.1': 'La Liga', 'ger.1': 'Bundesliga',
    'fra.1': 'Ligue 1', 'ita.1': 'Serie A', 'ned.1': 'Eredivisie',
    'por.1': 'Primeira Liga', 'usa.1': 'MLS', 'jpn.1': 'J1 League',
    'mex.1': 'Liga MX', 'bra.1': 'Brasileirão', 'arg.1': 'Liga Profesional',
    'tur.1': 'Süper Lig', 'bel.1': 'Belgian Pro League', 'sco.1': 'Scottish Premiership',
    'chn.1': 'Chinese Super League', 'sau.1': 'Saudi Pro League', 'kor.1': 'K League 1',
    'den.1': 'Danish Superliga', 'swe.1': 'Allsvenskan', 'swi.1': 'Swiss Super League',
    'gre.1': 'Super League Greece', 'ukr.1': 'Ukrainian Premier League', 'aus.1': 'A-League',
    'cze.1': 'Czech Liga', 'cro.1': 'HNL', 'ser.1': 'Serbian Super Liga',
    'pol.1': 'Ekstraklasa', 'aut.1': 'Austrian Bundesliga', 'saf.1': 'PSL',
    'egy.1': 'Egyptian Premier League', 'nga.1': 'NPFL', 'col.1': 'Categoría Primera A',
    'chi.1': 'Primera División', 'uru.1': 'Primera División', 'rou.1': 'Superliga',
    'rus.1': 'RPL', 'isr.1': "Ligat ha'Al", 'mor.1': 'Botola Pro',
    'nzl.1': 'A-League Men', 'idn.1': 'Liga 1', 'ven.1': 'Liga FUTVE',
    'par.1': 'División Profesional', 'bol.1': 'División Profesional',
    'crc.1': 'Liga Promerica', 'pan.1': 'LPF', 'hon.1': 'Liga Nacional',
    'jam.1': 'National Premier League', 'slv.1': 'Primera División',
    'mar.1': 'Botola Pro', 'sen.1': 'Ligue Sénégalaise', 'cmr.1': 'Elite One',
    'gnb.1': 'LFP', 'mlw.1': 'TNM Super League', 'tza.1': 'NBC Premier League',
    'irq.1': 'Iraqi Premier League', 'uae.1': 'UAE Pro League', 'kuw.1': 'Premier League',
    'jor.1': 'Jordan Premier League', 'ksa.1': 'Saudi Pro League',
    'uzb.1': 'Uzbekistan Super League',
}


def fetch_json(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception:
        return None


def get_all_wc_teams():
    d = fetch_json(f"{BASE}/FIFA.WORLD/teams?limit=100")
    if not d:
        return []
    raw = (d.get('sports') or [{}])[0].get('leagues', [{}])[0].get('teams', []) or d.get('teams', [])
    teams = []
    for t in raw:
        tm = t.get('team') or t
        if tm.get('id') and tm.get('displayName'):
            teams.append({'id': str(tm['id']), 'name': tm['displayName']})
    return sorted(teams, key=lambda x: x['name'])


def get_team_roster(team_id):
    d = fetch_json(f"{BASE}/FIFA.WORLD/teams/{team_id}/roster")
    if not d:
        return []
    return d.get('athletes', [])


def extract_league_and_club_id(athlete):
    league_ref   = (athlete.get('defaultLeague') or {}).get('$ref', '')
    team_ref     = (athlete.get('defaultTeam') or {}).get('$ref', '')
    league_slug  = ''
    club_team_id = ''
    if league_ref:
        m = re.search(r'leagues/([^?/]+)', league_ref)
        if m:
            league_slug = m.group(1)
    if team_ref:
        m = re.search(r'teams/(\d+)', team_ref)
        if m:
            club_team_id = m.group(1)
    return league_slug, club_team_id


def get_club_name(league_slug, club_team_id):
    d = fetch_json(f"{BASE}/{league_slug}/teams/{club_team_id}", timeout=8)
    if not d:
        return None
    team = d.get('team', {})
    return team.get('displayName') or team.get('name')


def main():
    print("Fetching all WC 2026 teams from ESPN...")
    teams = get_all_wc_teams()
    if not teams:
        print("ERROR: Could not fetch teams")
        return
    print(f"Found {len(teams)} teams")

    # Step 1: Fetch all rosters
    all_players = []
    print("\nFetching rosters...")
    for t in teams:
        athletes = get_team_roster(t['id'])
        print(f"  {t['name']}: {len(athletes)} players")
        for a in athletes:
            all_players.append((a, t['name']))
        time.sleep(0.1)

    print(f"\nTotal players: {len(all_players)}")

    # Step 2: Collect unique (league_slug, club_team_id) per player
    player_refs = {}
    for a, team_name in all_players:
        aid = str(a.get('id', ''))
        if not aid:
            continue
        league_slug, club_team_id = extract_league_and_club_id(a)
        if not league_slug or league_slug == 'fifa.world' or not club_team_id:
            continue
        player_refs[aid] = {
            'league_slug': league_slug,
            'club_team_id': club_team_id,
            'name': a.get('fullName') or a.get('displayName', ''),
            'team_name': team_name,
        }

    print(f"Players with club refs: {len(player_refs)}")

    # Step 3: Fetch club names for all unique (league, teamId) combos
    unique_combos = list({(v['league_slug'], v['club_team_id']) for v in player_refs.values()})
    print(f"\nFetching {len(unique_combos)} unique club names...")

    club_cache = {}

    def fetch_club(combo):
        league, tid = combo
        name = get_club_name(league, tid)
        return combo, name

    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = {ex.submit(fetch_club, c): c for c in unique_combos}
        done = 0
        for f in as_completed(futures):
            combo, name = f.result()
            if name:
                club_cache[combo] = name
            done += 1
            if done % 25 == 0:
                print(f"  {done}/{len(unique_combos)} clubs fetched...")

    print(f"Club names resolved: {len(club_cache)}/{len(unique_combos)}")

    # Step 4: Build output objects
    player_data = {}
    league_data = {}

    for aid, ref in player_refs.items():
        league_slug  = ref['league_slug']
        club_team_id = ref['club_team_id']
        club_name    = club_cache.get((league_slug, club_team_id))
        league_name  = LEAGUE_NAMES.get(league_slug, league_slug.upper())

        if club_name:
            player_data[aid] = {'club': club_name}
            league_data[aid] = league_name

    print(f"\nFinal: {len(player_data)} players with club + league data")

    # Step 5: Write JS output
    out_lines = [
        '// AUTO-GENERATED by generate_player_data.py — do not edit manually',
        f'// {len(player_data)} players across all 48 WC 2026 teams',
        '',
        'const PLAYER_DATA = ' + json.dumps(player_data, indent=2, ensure_ascii=False) + ';',
        '',
        'const LEAGUE_DATA = ' + json.dumps(league_data, indent=2, ensure_ascii=False) + ';',
    ]

    out_path = 'C:/Users/tobri/AIAgency/clients/worldcup/player_data_generated.js'
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out_lines))

    print(f"\nOutput written to {out_path}")

    # Coverage report
    team_coverage = {}
    for aid, ref in player_refs.items():
        tn = ref['team_name']
        team_coverage.setdefault(tn, {'total': 0, 'resolved': 0})
        team_coverage[tn]['total'] += 1
        if aid in player_data:
            team_coverage[tn]['resolved'] += 1

    print("\nCoverage by team:")
    for tn in sorted(team_coverage):
        c = team_coverage[tn]
        pct = int(100 * c['resolved'] / c['total']) if c['total'] else 0
        print(f"  {tn}: {c['resolved']}/{c['total']} ({pct}%)")


if __name__ == '__main__':
    main()
