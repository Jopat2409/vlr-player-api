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
# options.add_argument('--headless=new')
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


def __scrape_player_data(id: int, fromTimestamp: int = int((datetime.datetime.now() - datetime.timedelta(days=60)).timestamp())) -> dict:
    __driver.get(player_from_id(id)["url"])

    # go to the match history
    __driver.find_elements(By.CLASS_NAME, "wf-nav-item")[1].click()

    # 1v6 / 6ks are for the 0.01% chance someone clutches an ace with sage res
    return_stats = {
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
        "first-deaths": 0
    }
    current_match = 0
    current_page = 0
    extraStatsExist = True
    while(True):
        matches = __driver.find_element(By.CLASS_NAME, "mod-dark").find_elements(By.CLASS_NAME, 'wf-card')
        if current_match >= len(matches):
            current_page+=1
            pages = __driver.find_elements(By.CLASS_NAME, 'mod-page')
            if current_page >= len(pages): break
            pages[current_page].click()
            current_match = 0
            continue
        matches[current_match].click()
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
        print(f"Found match: {__driver.find_element(By.CLASS_NAME, 'match-header-event-series').text} on {match_date}")

        # parse match data
        # find player stats
        _xpath = f"//*[contains(text(), '{player_from_id(id)['display-name']}')]/../../../../td"
        # Get kda
        stats = __driver.find_elements(By.XPATH, _xpath)
        stats = stats[0:14] if isBO1 else stats[14:28]
        return_stats['kills'] += int(stats[4].find_element(By.CLASS_NAME, 'mod-both').text)
        return_stats['deaths'] += int(stats[5].find_element(By.CLASS_NAME, 'mod-both').text)
        return_stats['assists'] += int(stats[6].find_element(By.CLASS_NAME, 'mod-both').text)
        return_stats['first-bloods'] += int(stats[11].find_element(By.CLASS_NAME, 'mod-both').text)
        return_stats['first-deaths'] += int(stats[12].find_element(By.CLASS_NAME, 'mod-both').text)
        # get fk-fd and multikills / clutches

        if extraStatsExist:
            __driver.find_elements(By.CLASS_NAME, 'vm-stats-tabnav-item')[1].click()
            time.sleep(1)
            # Even though the stats ARE available, this div still exists on every page it is not displayed. EXCEPT NOT
            # ALL OF THEM SOMETIMES ITS JUST INEXPLICABLY NOT THERE WHICH IS HOW IT SHOULD BE I HATE THIS SITE
            potential_retarded_not_available = __driver.find_elements(By.XPATH, "//*[contains(text(), 'Stats from this map are not available yet')]")
            if potential_retarded_not_available and potential_retarded_not_available[0].find_element(By.XPATH, "..").get_attribute("data-game-id") == "all":
                print("Could not find extra statters")
                extraStatsExist = False
                continue
            _xpath = f"//td/div/div[contains(text(), '{player_from_id(id)['display-name']}')]/../../.."
            stats_tr = __driver.find_elements(By.XPATH, _xpath)
            stats_tr = (stats_tr[7] if isBO1 else stats_tr[3]).find_elements(By.TAG_NAME, 'td')

            return_stats["multikills"]["3k"] += __parse_egg(stats_tr[3])
            return_stats["multikills"]["4k"] += __parse_egg(stats_tr[4])
            return_stats["multikills"]["5k"] += __parse_egg(stats_tr[5])

            return_stats["clutches"]["1v1"] += __parse_egg(stats_tr[6])
            return_stats["clutches"]["1v2"] += __parse_egg(stats_tr[7])
            return_stats["clutches"]["1v3"] += __parse_egg(stats_tr[8])
            return_stats["clutches"]["1v4"] += __parse_egg(stats_tr[9])
            return_stats["clutches"]["1v5"] += __parse_egg(stats_tr[10])

        __driver.back()
        current_match += 1
    return return_stats


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
        return_results.append({
            "display-name": result.find(class_="team-roster-item-name-alias").text.strip(),
            "real-name": result.find(class_="team-roster-item-name-real").text.strip(),
            "team": tag,
            "team-id": team["id"],
            "url": f"https://www.vlr.gg{result.find('a', href=True)['href']}",
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
    with open("data.json", "w", encoding='utf-8') as f:
        json.dump(STATIC_DAT, f, indent=2)


if __name__ == "__main__":
    _inp = int(input("1. Run Tests\n2. Re-scrape Data\n>>> "))
    if _inp == 1:
        pass
    if _inp == 2:
        __scrape_all_data()

