from __future__ import annotations
import requests
import json
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import datetime

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
    WebDriverWait(__driver, 20).until(EC.presence_of_element_located((By.CLASS_NAME, 'ncmp__btn')))
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

def __scrape_player_data(id: int, fromTimestamp: int = int((datetime.datetime.now() - datetime.timedelta(days=60)).timestamp())) -> dict:
    __driver.get(player_from_id(id)["url"])

    # go to the match history
    __driver.find_elements(By.CLASS_NAME, "wf-nav-item")[1].click()

    current_match = 0
    current_page = 0
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

        # we stop looking at matches when they are earlier than the desired timestamp
        match_date = __driver.find_elements(By.CLASS_NAME, 'moment-tz-convert')[0].get_attribute('data-utc-ts')
        match_epoch = datetime.datetime.strptime(match_date, '%Y-%m-%d %H:%M:%S').timestamp()
        if match_epoch < fromTimestamp: break

        print(f"Found match: {__driver.find_element(By.CLASS_NAME, 'match-header-event-series').text} on {match_date}")

        # parse match data

        __driver.back()
        current_match += 1
    return {
        "kills": 0,
        "deaths": 0,
        "assists": 0,
        "first-kills": 0,
        "first-deaths": 0
    }


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

def player_stats_from_id(id: int) -> dict:
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
    return {"data": player_from_id(id), "stats": __scrape_player_data(id)}


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

