from __future__ import annotations
import requests
import json
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

STATIC_DAT = {}
options = Options()
# options.add_argument('--headless=new')
__driver = webdriver.Chrome(options=options)


def init():
    global STATIC_DAT
    with open("data.json", "r") as f:
        STATIC_DAT = json.load(f)



def get_teams() -> dict:
    return STATIC_DAT["tier1"]["teams"]

def team_from_id(id: int) -> dict:
    return next(team for team in get_teams() if int(team["id"]) == id)

def get_players() -> list:
    return [player for team in get_teams() for player in team["players"]]

def player_from_id(id: int) -> dict:
    #TODO: Add id field to player also why is it url in player but vlr-url in team
    return next(player for player in get_players() if str(id) in player["url"])

def __scrape_player_data(id: int) -> dict:
    __driver.get(player_from_id(id)["url"])
    # get rid of retarded cookie popup
    __driver.find_elements(By.CLASS_NAME, 'ncmp__btn')[1].click()
    # go to the match history
    __driver.find_elements(By.CLASS_NAME, "wf-nav-item")[1].click()

    current_match = 0
    while(current_match < 10):
        matches = __driver.find_element(By.CLASS_NAME, "mod-dark").find_elements(By.CLASS_NAME, 'wf-card')
        matches[current_match].click()

        match_date = __driver.find_elements(By.CLASS_NAME, 'moment-tz-convert')[0].text
        print(f"Found match: {__driver.find_element(By.CLASS_NAME, 'match-header-event-series').text} on {match_date}")

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

