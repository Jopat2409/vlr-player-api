from __future__ import annotations
import datetime
import requests
import json
import time
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium import webdriver
from bs4 import BeautifulSoup

STATIC_DAT = {}
options = Options()
options.add_argument('--headless=new')
__driver = webdriver.Chrome(options=options)


def init():
    global STATIC_DAT
    with open("data.json", "r") as f:
        STATIC_DAT = json.load(f)

    # get rid of retardewd cookie popup x2
    __driver.get("https://www.vlr.gg")
    WebDriverWait(__driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, 'ncmp__btn')))
    # get rid of retarded cookie popup
    __driver.find_elements(By.CLASS_NAME, 'ncmp__btn')[1].click()




def get_teams() -> dict:
    return STATIC_DAT["tier1"]["teams"]

def team_from_id(id: int) -> dict:
    return next(team for team in get_teams() if int(team["id"]) == id)

def get_players() -> list:
    return [player for team in get_teams() for player in team["players"]]

def player_from_id(id: int) -> dict:
    #TODO: Add id field to player also why is it url in player but vlr-url in team
    return next(player for player in get_players() if str(id) in player["url"])


def __parse_egg(div):
    text = div.find_element(By.CLASS_NAME, 'stats-sq').text
    if text:
        return int(text)
    return 0


def __scrape_player_data(id: int, fromTimestamp: int = int((datetime.datetime.now() - datetime.timedelta(days=60)).timestamp())) -> list:
    __driver.get(player_from_id(id)["url"])

    # go to the match history
    __driver.find_elements(By.CLASS_NAME, "wf-nav-item")[1].click()

    # 1v6 / 6ks are for the 0.01% chance someone clutches an ace with sage res
    current_match = 0
    current_page = 0
    return_matches = []
    while(True):
        matches = __driver.find_element(By.CLASS_NAME, "mod-dark").find_elements(By.CLASS_NAME, 'wf-card')
        if current_match >= len(matches):
            current_page+=1
            pages = __driver.find_elements(By.CLASS_NAME, 'mod-page')
            if current_page >= len(pages):
                print("we breaking")
                break
            pages[current_page].click()
            current_match = 0
            continue
        matches[current_match].click()
        current_match_stats = {
            "timestamp": 0,
            "kills": 0,
            "assists": 0,
            "deaths": 0,
            "clutches": {
                "1v1": 0,
                "1v2": 0,
                "1v3": 0,
                "1v4": 0,
                "1v5": 0,
                "1v6": 0
            },
            "multikills": {
                "3k": 0,
                "4k": 0,
                "5k": 0,
                "6k": 0
            },
            "first-bloods": 0,
            "first-deaths": 0,
            "spike-plants": 0,
            "spike-defuses": 0
        }
        isBO1 = False
        try:
            WebDriverWait(__driver, 0.5).until(EC.presence_of_element_located((By.CLASS_NAME, 'vm-stats-gamesnav-item')))
            # Ensure we are on the overview page
            __driver.find_elements(By.CLASS_NAME, 'vm-stats-gamesnav-item')[0].click()
        except TimeoutException:
            isBO1 = True

        # we stop looking at matches when they are earlier than the desired timestamp
        match_date = __driver.find_elements(By.CLASS_NAME, 'moment-tz-convert')[0].get_attribute('data-utc-ts')
        match_epoch = datetime.datetime.strptime(match_date, '%Y-%m-%d %H:%M:%S').timestamp()
        if match_epoch < fromTimestamp: break
        current_match_stats["timestamp"] = match_epoch
        print(f"Found match: {__driver.find_element(By.CLASS_NAME, 'match-header-event-series').text} on {match_date}")

        # parse match data
        # find player stats
        _xpath = f"//*[contains(text(), '{player_from_id(id)['display-name']}')]/../../../../td"
        # Get kda
        _stats = __driver.find_elements(By.XPATH, _xpath)
        statsFound = False
        for start in range(0,42,14):
            try:
                stats = _stats[start:start+14]
                current_match_stats['kills'] += int(stats[4].find_element(By.CLASS_NAME, 'mod-both').text)
                current_match_stats['deaths'] += int(stats[5].find_element(By.CLASS_NAME, 'mod-both').text)
                current_match_stats['assists'] += int(stats[6].find_element(By.CLASS_NAME, 'mod-both').text)
                current_match_stats['first-bloods'] += int(stats[11].find_element(By.CLASS_NAME, 'mod-both').text)
                current_match_stats['first-deaths'] += int(stats[12].find_element(By.CLASS_NAME, 'mod-both').text)
                statsFound = True
                break
            except ValueError:
                pass
            except IndexError:
                statsFound = False

        if statsFound:
            # get fk-fd and multikills / clutches
            _xpath = f"//*[contains(text(), '{player_from_id(id)['display-name']}')]/../../.."

            __driver.find_elements(By.CLASS_NAME, 'vm-stats-tabnav-item')[1].click()
            # this dogshit site takes ages to load so wait a min of 0.5s
            WebDriverWait(__driver, 5).until(EC.presence_of_element_located((By.XPATH, _xpath)))
            time.sleep(0.5)
            # Even though the stats ARE available, this div still exists on every page it is not displayed. EXCEPT NOT
            # ALL OF THEM SOMETIMES ITS JUST INEXPLICABLY NOT THERE WHICH IS HOW IT SHOULD BE I HATE THIS SITE
            potential_retarded_not_available = __driver.find_elements(By.XPATH, "//*[contains(text(), 'Stats from this map are not available yet')]")
            if not(potential_retarded_not_available and potential_retarded_not_available[0].find_element(By.XPATH, "..").get_attribute("data-game-id") == "all"):
                stats_tr = __driver.find_elements(By.XPATH, _xpath)
                stats_tr = (stats_tr[7] if isBO1 else stats_tr[3]).find_elements(By.TAG_NAME, 'td')

                current_match_stats["multikills"]["3k"] += __parse_egg(stats_tr[3])
                current_match_stats["multikills"]["4k"] += __parse_egg(stats_tr[4])
                current_match_stats["multikills"]["5k"] += __parse_egg(stats_tr[5])

                current_match_stats["clutches"]["1v1"] += __parse_egg(stats_tr[6])
                current_match_stats["clutches"]["1v2"] += __parse_egg(stats_tr[7])
                current_match_stats["clutches"]["1v3"] += __parse_egg(stats_tr[8])
                current_match_stats["clutches"]["1v4"] += __parse_egg(stats_tr[9])
                current_match_stats["clutches"]["1v5"] += __parse_egg(stats_tr[10])
                current_match_stats["spike-plants"] += __parse_egg(stats_tr[12])
                current_match_stats["spike-defuses"] += __parse_egg(stats_tr[13])
            else:
                print("Could not find statters")

        __driver.back()
        current_match += 1
        return_matches.append(current_match_stats)
    return return_matches


def __scrape_players_from_team(id: int) -> list:
    """ Returns in dictionary form
    [
    {
        "name": "Boostio",
        "team": "100T",
        "team-id": 120,
        "player-id": <player-id>,
        "url": <vlr-url>
    }
    ]
    """
    team = team_from_id(id)
    url, tag = team["vlr-url"], team["display-tag"]

    soup = BeautifulSoup(requests.get(url).content, "html.parser")
    return_results = []
    results = soup.find_all("div", class_="team-roster-item")

    for result in results:
        player_url = result.find('a', href=True)['href']
        player_id = int(player_url.split("/")[2])
        return_results.append({
            "display-name": result.find(class_="team-roster-item-name-alias").text.strip(),
            "real-name": result.find(class_="team-roster-item-name-real").text.strip(),
            "team": tag,
            "team-id": team["id"],
            "player-id": player_id,
            "url": f"https://www.vlr.gg{player_url}",
            "role": "igl" if result.find(title="Team Captain") else "coach" if result.find(class_="team-roster-item-name-role") else "player"
        })

    return return_results

def player_stats_from_id(id: int, timeframe: int) -> dict:
    """
    {
        kills
        deaths
        assists
        rating
        plants
        defuses
        3ks
        4ks
        aces
        first-kills
        first-deaths
    }
    """

    return {"data": player_from_id(id), "stats": __scrape_player_data(id, timeframe)}


def __scrape_all_data():
    print("Scraping team data for all VCT partnered teams")
    init()
    for i, team in enumerate(get_teams()):
        STATIC_DAT["tier1"]["teams"][i].update({"players": __scrape_players_from_team(int(team["id"]))})
    for player in get_players():
        if str(player["player-id"]) in STATIC_DAT["tier1"]["players"]:
            print(f"Skipping: {player['display-name']}")
            continue
        match_stats = __scrape_player_data(player['player-id'], 0)
        STATIC_DAT["tier1"]["players"][str(player["player-id"])] = match_stats
        with open("data.json", "w", encoding='utf-8') as f:
            json.dump(STATIC_DAT, f, indent=2)


if __name__ == "__main__":
    _inp = int(input("1. Run Tests\n2. Re-scrape Data\n>>> "))
    if _inp == 1:
        pass
    if _inp == 2:
        __scrape_all_data()

