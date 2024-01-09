from __future__ import annotations
import json
import requests
from bs4 import BeautifulSoup

STATIC_DAT = {}

def load_data():
    global STATIC_DAT
    with open("data.json", "r") as f:
        STATIC_DAT = json.load(f)


def get_teams() -> dict:
    return STATIC_DAT["tier1"]["teams"]

def team_from_id(id: int) -> dict:
    return next(team for team in get_teams() if int(team["id"]) == id)

def players_from_team(id: int) -> list:
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
            "url": f"https://www.vlr.gg{result.find('a', href=True)['href']}"
        })

    return return_results

def player_stats_from_id(id: int) -> dict:
    """
    {
        kills
        assists

    }
    """


def __scrape_all_data():
    print("Scraping team data for all VCT partnered teams")
    load_data()
    to_save = []
    for team in get_teams():
        to_save += players_from_team(team["id"])
    STATIC_DAT["tier1"].update({"players": to_save})
    with open("data.json", "w", encoding='utf-8') as f:
        json.dump(STATIC_DAT, f, indent=2)


if __name__ == "__main__":
    _inp = int(input("1. Run Tests\n2. Re-scrape Data\n>>>"))
    if _inp == 1:
        pass
    if _inp == 2:
        __scrape_all_data()

