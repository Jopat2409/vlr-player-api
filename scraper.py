import requests
import datetime
import sys
import time
import debugdgers
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium import webdriver
from bs4 import BeautifulSoup


_BASE_MATCH = {
    "match-name": "",
            "timestamp": 0,
            "rating": 0,
            "acs": 0,
            "kills": 0,
            "deaths": 0,
            "assists": 0,
            "KAST":0,
            "ADR":0,
            "HS":0,
            "first-bloods":0,
            "first-deaths": 0,
            "multikills": {
                "3k": 0,
                "4k": 0,
                "5k": 0
            },
            "clutches": {
                "1v1": 0,
                "1v2": 0,
                "1v3": 0,
                "1v4": 0,
                "1v5": 0
            },
            "spike-plants": 0,
            "spike-defuses": 0

}


class Scraper:

    def __init__(self):
        options = Options()
        options.add_argument("--headless=new")
        self.__driver = webdriver.Chrome(options=options)
        self.__remove_cookies()
    
    def __del__(self):
        self.__driver.quit()

    def __remove_cookies(self):
        self.__driver.get("https://www.vlr.gg")
        WebDriverWait(self.__driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, 'ncmp__btn')))
        # get rid of retarded cookie popup
        self.__driver.find_elements(By.CLASS_NAME, 'ncmp__btn')[1].click()

    def get_match_id(self, url: str) -> int:
        soup = BeautifulSoup(requests.get(url).content, 'html.parser')
        return int(soup.find_all(class_ = "vm-stats")[0]['data-match-id'])
    
    def __parse_egg(self, item, _type=int):
        return _type(item.get_attribute('innerHTML').rstrip().replace('%', '').replace("&nbsp;", '').replace(u'\xa0', u' ').replace('\n', '').replace('\t', '') or 0)


    def get_match_urls(self, player: int) -> list[str]:
        soup = BeautifulSoup(requests.get(f"https://www.vlr.gg/player/matches/{player}").content, 'html.parser')
        num_pages = len(soup.find_all(class_='mod-page'))
        r_urls = []
        for i in range(num_pages):
            soup = BeautifulSoup(requests.get(f"https://www.vlr.gg/player/matches/{player}?page={i}").content, 'html.parser')
            matches = soup.find(class_="mod-dark").find_all(class_='wf-card')
            r_urls += ['https://vlr.gg' + str(href['href']) for href in matches]
        return r_urls
    

    def get_end_timestamps(self, player: int) -> tuple[int]:
        #TODO: Fix the fact that sometimes there is just no matches on the last page
        soup = BeautifulSoup(requests.get(f"https://www.vlr.gg/player/matches/{player}").content, 'html.parser')
        last_match = soup.find(class_='wf-card', href=True)['href']
        last_timestamp = self.get_match_stats(f"https://www.vlr.gg{last_match}")['timestamp']

        last_page = int(soup.find_all(class_='mod-page')[-1].text)
        soup = BeautifulSoup(requests.get(f"https://www.vlr.gg/player/matches/{player}?page={last_page}").content, 'html.parser')
        first_match = soup.find_all(class_='wf-card', href=True)[-1]['href']
        first_timestamp = self.get_match_stats(f"https://www.vlr.gg{first_match}")['timestamp']

        return last_timestamp, first_timestamp

    def get_match_stats(self, url: str) -> dict:
        soup = BeautifulSoup(requests.get(url).content, 'html.parser')
        match_date = soup.find_all(class_='moment-tz-convert')[0]['data-utc-ts']
        match_epoch = datetime.datetime.strptime(match_date, '%Y-%m-%d %H:%M:%S').timestamp()
        match_title = str(soup.find(class_='match-header-event-series').text.strip().replace('\n', '').replace('\t', ''))
        return {
            "title": ' '.join(match_title.split()),
            "timestamp": match_epoch
        }


    
    def scrape_matches(self, player) -> dict:
        """
        Scrapes the stats for every match in a player's 
        """
        for m in self.get_match_urls(player.player_id):
            yield self.scrape_match(m, player.display_name)
    
    def __parse_player_stat_egg(self, egg, _type=float):
        return self.__parse_egg(egg.find_element(By.CLASS_NAME, 'mod-both'), _type)

    
    @debugdgers.timer
    def scrape_match(self, url: str) -> dict:
        self.__driver.get(url)

        match_date = self.__driver.find_elements(By.CLASS_NAME, 'moment-tz-convert')[0].get_attribute('data-utc-ts')
        match_epoch = datetime.datetime.strptime(match_date, '%Y-%m-%d %H:%M:%S').timestamp()

        event_name = self.__parse_egg(self.__driver.find_element(By.XPATH, "//a[contains(@class, 'match-header-event')]//div//div"), str)
        match_title = self.__parse_egg(self.__driver.find_element(By.CLASS_NAME, 'match-header-event-series'), str)

        return_stats = {"match-data": {}, "match-stats":{}}
        return_stats["match-data"]["timestamp"] = match_epoch
        return_stats["match-data"]["event-name"] = event_name
        return_stats["match-data"]["match-title"] = match_title

        player_stat_data = self.__driver.find_elements(By.XPATH, "//div[@data-game-id != 'all' and contains(@class,'vm-stats-game ')]//tr//td[@class='mod-player']/..//td")
        for i in range(0, len(player_stat_data), 14):
            stats = player_stat_data[i:i+14]
            player_name = self.__parse_egg(stats[0].find_element(By.CLASS_NAME, 'text-of'), str)
            return_stats["match-stats"][player_name] = return_stats["match-stats"].get(player_name, [])
            return_stats["match-stats"][player_name].append({
                "rating": self.__parse_player_stat_egg(stats[2], float),
                "acs": self.__parse_player_stat_egg(stats[3]),
                "kills": self.__parse_player_stat_egg(stats[4]),
                "deaths": self.__parse_player_stat_egg(stats[5]),
                "assists": self.__parse_player_stat_egg(stats[6]),
                "KAST": self.__parse_player_stat_egg(stats[8]),
                "ADR": self.__parse_player_stat_egg(stats[9]),
                "HS": self.__parse_player_stat_egg(stats[10]),
                "first-bloods": self.__parse_player_stat_egg(stats[11]),
                "first-deaths": self.__parse_player_stat_egg(stats[12]),
                "multikills": {
                    "3k": 0,
                    "4k": 0,
                    "5k": 0
                },
                "clutches": {
                    "1v1": 0,
                    "1v2": 0,
                    "1v3": 0,
                    "1v4": 0,
                    "1v5": 0
                },
                "spike-plants": 0,
                "spike-defuses": 0               
            })
            
        self.__driver.find_elements(By.CLASS_NAME, 'vm-stats-tabnav-item')[1].click()
        time.sleep(0.75)
        if self.__driver.find_elements(By.XPATH, "//div[contains(@data-game-id, 'all')]/div[contains(text(), 'Stats from this map are not available yet')]"):
            print("Potentially no statters")
            self.__driver.back()
            return return_stats
        player_stats_tr = self.__driver.find_elements(By.XPATH, "//div[@data-game-id != 'all' and contains(@class,'vm-stats-game ')]//tr")
        for i in range(19, len(player_stats_tr), 29):
            player_stats = player_stats_tr[i:i+10]
            game_no = int((i-19)/29)
            for _tr in player_stats_tr[i:i+10]:
                stats = [td.find_element(By.CLASS_NAME, "stats-sq") for td in _tr.find_elements(By.TAG_NAME, "td")]
                print(f"Stats: {stats}")
                return_stats["match-data"][player_name][game_no]["multikills"]["3k"] = self.__parse_egg(stats[3])
                return_stats["match-data"][player_name][game_no]["multikills"]["4k"] = self.__parse_egg(stats[4])
                return_stats["match-data"][player_name][game_no]["multikills"]["5k"] = self.__parse_egg(stats[5])

                return_stats["match-data"][player_name][game_no]["clutches"]["1v1"] = self.__parse_egg(stats[6])
                return_stats["match-data"][player_name][game_no]["clutches"]["1v2"] = self.__parse_egg(stats[7])
                return_stats["match-data"][player_name][game_no]["clutches"]["1v3"] = self.__parse_egg(stats[8])
                return_stats["match-data"][player_name][game_no]["clutches"]["1v4"] = self.__parse_egg(stats[9])
                return_stats["match-data"][player_name][game_no]["clutches"]["1v5"] = self.__parse_egg(stats[10])

                return_stats["match-data"][player_name][game_no]["spike-plants"] = self.__parse_egg(stats[12])
                return_stats["match-data"][player_name][game_no]["spike-defuses"] = self.__parse_egg(stats[13])
        self.__driver.back()
        print(return_stats)
        return return_stats
    
    def scrape_player_matches(self, player):
        self.__driver.get(f"https://www.vlr.gg/player/matches/{player.player_id}")

        pages = self.__driver.find_elements(By.CLASS_NAME, 'mod-page')

        for i in range(len(pages)):
            pages = self.__driver.find_elements(By.CLASS_NAME, "mod-page")
            pages[i].click()
            page_urls = [elem.get_attribute('href') for elem in self.__driver.find_element(By.CLASS_NAME, "mod-dark").find_elements(By.CLASS_NAME, 'wf-card')]
            for url in page_urls:
                yield self.scrape_match_selenium(url, player.display_name)
                                            
vlr_scraper = Scraper()

if __name__ == "__main__":
    vlr_scraper.scrape_match("https://www.vlr.gg/294973/team-ludwig-vs-team-tarik-ludwig-x-tarik-invitational-2-match")