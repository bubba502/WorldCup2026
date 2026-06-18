#!/usr/bin/env python3
"""
Merge ESPN-generated player data with original 4-team static data.
Run after generate_player_data.py. Output: player_data_merged.js
"""
import re, json

ORIGINAL_CLUBS = {
    "290899":"Chivas de Guadalajara","259975":"Genoa CFC","224323":"Monterrey",
    "276942":"Cruz Azul","132098":"Monterrey","290414":"Club America",
    "283827":"Club America","303577":"Club America","233075":"Club America",
    "194308":"Chivas de Guadalajara","167060":"Fulham FC","242614":"Cruz Azul",
    "265969":"Pumas UNAM","137038":"Club America","236368":"Santos Laguna",
    "104497":"Pachuca","379193":"Club America","260775":"Bayer Leverkusen",
    "318554":"Seattle Sounders FC","229487":"Chivas de Guadalajara",
    "193566":"Puebla FC","376110":"Queretaro FC","389575":"Club America",
    "241627":"West Ham United","178746":"Porto","207011":"AEK Athens",
    "196230":"Mamelodi Sundowns","358744":"Mamelodi Sundowns","400594":"Mamelodi Sundowns",
    "266125":"Mamelodi Sundowns","223818":"Mamelodi Sundowns","276767":"Mamelodi Sundowns",
    "228595":"Mamelodi Sundowns","304736":"Charlotte FC","256691":"SuperSport United",
    "264751":"Burnley FC","291141":"Stellenbosch FC","288771":"Polokwane City",
    "265713":"Stellenbosch FC","157046":"Mamelodi Sundowns","337134":"Mamelodi Sundowns",
    "390448":"AmaZulu FC","365623":"Kaizer Chiefs","366883":"Mamelodi Sundowns",
    "361211":"Orlando Pirates","301321":"AmaZulu FC","186121":"Kaizer Chiefs",
    "310593":"Cape Town City","335450":"Chippa United","313399":"Sekhukhune United",
    "303312":"Bayer Leverkusen","351372":"Mamelodi Sundowns",
    "175921":"FC Tokyo","230244":"Jeonbuk Hyundai Motors","256724":"Ulsan HD FC",
    "157688":"Bayern Munich","280060":"Jeonbuk Hyundai Motors","286268":"Kashima Antlers",
    "297270":"Jeonbuk Hyundai Motors","297788":"FC Seoul","302793":"Suwon Samsung Bluewings",
    "345769":"Ulsan HD FC","3098209":"Ulsan HD FC","90721":"Jeonbuk Hyundai Motors",
    "134103":"1. FSV Mainz 05","256598":"Jeonbuk Hyundai Motors","271702":"Ulsan HD FC",
    "274197":"Paris Saint-Germain","280061":"Feyenoord Rotterdam","304793":"Jeonbuk Hyundai Motors",
    "336178":"Zhejiang Professional FC","362208":"Jeonbuk Hyundai Motors","149945":"LAFC",
    "237224":"Wolverhampton Wanderers","297791":"Jeonbuk Hyundai Motors","302434":"KAA Gent",
    "303464":"SC Freiburg","350711":"Celtic FC",
    "199988":"Slavia Prague","277313":"PSV Eindhoven","319267":"FC Viktoria Plzen",
    "151714":"Sparta Prague","191209":"West Ham United","276659":"Banik Ostrava",
    "280885":"Club Brugge","290116":"Torino FC","322510":"ACF Fiorentina",
    "335996":"SL Benfica","370744":"Slavia Prague","165637":"Slavia Prague",
    "230666":"West Ham United","249525":"FC Twente","294618":"Slavia Prague",
    "303726":"Slavia Prague","305545":"Olympique Lyonnais","310027":"Sparta Prague",
    "343937":"Slavia Prague","387865":"FK Jablonec","403974":"Slavia Prague",
    "212330":"Bayer Leverkusen","257336":"Sparta Prague","292169":"Bayer Leverkusen",
    "306008":"Sparta Prague","343733":"RB Leipzig",
}

ORIGINAL_LEAGUES = {
    "290899":"Liga MX","259975":"Serie A","224323":"Liga MX","276942":"Liga MX",
    "132098":"Liga MX","290414":"Liga MX","283827":"Liga MX","303577":"Liga MX",
    "233075":"Liga MX","194308":"Liga MX","167060":"Premier League","242614":"Liga MX",
    "265969":"Liga MX","137038":"Liga MX","236368":"Liga MX","104497":"Liga MX",
    "379193":"Liga MX","260775":"Bundesliga","318554":"MLS","229487":"Liga MX",
    "193566":"Liga MX","376110":"Liga MX","389575":"Liga MX","241627":"Premier League",
    "178746":"Primeira Liga","207011":"Super League Greece",
    "196230":"PSL","358744":"PSL","400594":"PSL","266125":"PSL","223818":"PSL",
    "276767":"PSL","228595":"PSL","304736":"MLS","256691":"PSL","264751":"Championship",
    "291141":"PSL","288771":"PSL","265713":"PSL","157046":"PSL","337134":"PSL",
    "390448":"PSL","365623":"PSL","366883":"PSL","361211":"PSL","301321":"PSL",
    "186121":"PSL","310593":"PSL","335450":"PSL","313399":"PSL","303312":"Bundesliga",
    "351372":"PSL",
    "175921":"J1 League","230244":"K League 1","256724":"K League 1",
    "157688":"Bundesliga","280060":"K League 1","286268":"J1 League",
    "297270":"K League 1","297788":"K League 1","302793":"K League 1",
    "345769":"K League 1","3098209":"K League 1","90721":"K League 1",
    "134103":"Bundesliga","256598":"K League 1","271702":"K League 1",
    "274197":"Ligue 1","280061":"Eredivisie","304793":"K League 1",
    "336178":"Chinese Super League","362208":"K League 1","149945":"MLS",
    "237224":"Premier League","297791":"K League 1","302434":"Belgian Pro League",
    "303464":"Bundesliga","350711":"Scottish Premiership",
    "199988":"Czech Liga","277313":"Eredivisie","319267":"Czech Liga",
    "151714":"Czech Liga","191209":"Premier League","276659":"Czech Liga",
    "280885":"Belgian Pro League","290116":"Serie A","322510":"Serie A",
    "335996":"Primeira Liga","370744":"Czech Liga","165637":"Czech Liga",
    "230666":"Premier League","249525":"Eredivisie","294618":"Czech Liga",
    "303726":"Czech Liga","305545":"Ligue 1","310027":"Czech Liga",
    "343937":"Czech Liga","387865":"Czech Liga","403974":"Czech Liga",
    "212330":"Bundesliga","257336":"Czech Liga","292169":"Bundesliga",
    "306008":"Czech Liga","343733":"Bundesliga",
}

SALARY = {
    "290899":"~$1.8M","259975":"~$3.5M","224323":"~$2.8M","276942":"~$1.6M",
    "132098":"~$2.5M","290414":"~$1.5M","283827":"~$2.8M","303577":"~$2.2M",
    "233075":"~$2.5M","194308":"~$2.0M","167060":"~$6.2M","242614":"~$1.8M",
    "265969":"~$1.4M","137038":"~$2.5M","236368":"~$1.2M","104497":"~$3.2M",
    "379193":"~$1.2M","260775":"~$12.0M","318554":"~$2.4M","229487":"~$2.2M",
    "193566":"~$1.0M","376110":"~$0.8M","389575":"~$0.9M","241627":"~$8.5M",
    "178746":"~$3.8M","207011":"~$2.8M",
    "196230":"~$1.5M","358744":"~$0.8M","400594":"~$0.7M","266125":"~$0.9M",
    "223818":"~$0.8M","276767":"~$0.9M","228595":"~$0.8M","304736":"~$1.8M",
    "256691":"~$1.0M","264751":"~$3.2M","291141":"~$0.7M","288771":"~$0.5M",
    "265713":"~$0.5M","157046":"~$1.2M","337134":"~$0.6M","390448":"~$0.5M",
    "365623":"~$0.5M","366883":"~$0.6M","361211":"~$1.6M","301321":"~$0.6M",
    "186121":"~$0.6M","310593":"~$0.5M","335450":"~$0.4M","313399":"~$0.4M",
    "303312":"~$4.5M","351372":"~$0.5M",
    "175921":"~$0.8M","230244":"~$0.5M","256724":"~$0.4M","157688":"~$14.0M",
    "280060":"~$0.5M","286268":"~$0.6M","297270":"~$0.3M","297788":"~$0.4M",
    "302793":"~$0.4M","345769":"~$0.4M","3098209":"~$0.3M","90721":"~$0.4M",
    "134103":"~$3.5M","256598":"~$0.5M","271702":"~$0.6M","274197":"~$12.0M",
    "280061":"~$4.0M","304793":"~$0.3M","336178":"~$1.8M","362208":"~$0.4M",
    "149945":"~$8.0M","237224":"~$5.0M","297791":"~$0.4M","302434":"~$1.5M",
    "303464":"~$3.0M","350711":"~$2.5M",
    "199988":"~$1.5M","277313":"~$4.0M","319267":"~$0.6M","151714":"~$0.8M",
    "191209":"~$4.5M","276659":"~$0.5M","280885":"~$3.5M","290116":"~$2.0M",
    "322510":"~$3.0M","335996":"~$3.5M","370744":"~$0.6M","165637":"~$0.7M",
    "230666":"~$6.0M","249525":"~$3.0M","294618":"~$1.2M","303726":"~$0.9M",
    "305545":"~$4.5M","310027":"~$0.5M","343937":"~$0.6M","387865":"~$0.4M",
    "403974":"~$0.5M","212330":"~$9.0M","257336":"~$1.0M","292169":"~$6.0M",
    "306008":"~$1.2M","343733":"~$3.5M",
}


def main():
    with open('C:/Users/tobri/AIAgency/clients/worldcup/player_data_generated.js', encoding='utf-8') as f:
        src = f.read()
    espn_player = json.loads(re.search(r'const PLAYER_DATA = (\{.*?\});', src, re.DOTALL).group(1))
    espn_league = json.loads(re.search(r'const LEAGUE_DATA = (\{.*?\});', src, re.DOTALL).group(1))

    # Load Capology salaries (primary source) — falls back to hardcoded SALARY dict
    capology_salary = {}
    capology_path = 'C:/Users/tobri/AIAgency/clients/worldcup/salary_capology.json'
    try:
        with open(capology_path, encoding='utf-8') as f:
            capology_salary = json.load(f)
        print(f"Loaded {len(capology_salary)} Capology salaries")
    except FileNotFoundError:
        print("No salary_capology.json found — using hardcoded SALARY only")

    all_ids = set(list(espn_player) + list(ORIGINAL_CLUBS) + list(SALARY) + list(capology_salary))
    merged_player, merged_league = {}, {}

    for aid in all_ids:
        entry = {}
        club = espn_player.get(aid, {}).get('club') or ORIGINAL_CLUBS.get(aid)
        if club:
            entry['club'] = club
        # Capology takes priority over hardcoded estimates
        salary = capology_salary.get(aid) or SALARY.get(aid)
        if salary:
            entry['salary'] = salary
        if entry:
            merged_player[aid] = entry
        league = espn_league.get(aid) or ORIGINAL_LEAGUES.get(aid)
        if league:
            merged_league[aid] = league

    cap_count = sum(1 for aid in merged_player if aid in capology_salary)
    hc_count  = sum(1 for aid in merged_player if aid in SALARY and aid not in capology_salary)
    print(f"PLAYER_DATA: {len(merged_player)} | club: {sum(1 for v in merged_player.values() if 'club' in v)} | salary: {sum(1 for v in merged_player.values() if 'salary' in v)} (capology: {cap_count}, hardcoded: {hc_count})")
    print(f"LEAGUE_DATA: {len(merged_league)}")

    out = (
        '// AUTO-GENERATED — regenerate with generate_player_data.py + merge_player_data.py\n'
        f'// {len(merged_player)} players\n\n'
        'const PLAYER_DATA = ' + json.dumps(merged_player, indent=2, ensure_ascii=False) + ';\n\n'
        'const LEAGUE_DATA = ' + json.dumps(merged_league, indent=2, ensure_ascii=False) + ';\n'
    )
    out_path = 'C:/Users/tobri/AIAgency/clients/worldcup/player_data_merged.js'
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(out)
    print(f"Written {out_path}")


if __name__ == '__main__':
    main()
