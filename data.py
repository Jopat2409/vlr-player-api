from __future__ import annotations
from typing import List
import sqlalchemy as db
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base, sessionmaker, mapped_column, relationship, Mapped
from scraper import vlr_scraper
import time

metadata = db.MetaData()
Base = declarative_base(metadata=metadata)
engine = db.create_engine("sqlite:///db.sqlite")


class Player(Base):
    __tablename__ = "players"
    player_id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(db.ForeignKey("teams.team_id"))
    display_name: Mapped[str] = mapped_column()
    real_name: Mapped[str] = mapped_column()
    role: Mapped[str] = mapped_column()

    def url(self) -> str:
        return f"https://www.vlr.gg/player/{self.player_id}"
    
    def is_complete(self) -> bool:
        last, first = vlr_scraper.get_end_timestamps(self.player_id)
        #print(last, first)
        return vlr_db.match_stats_exist(self.player_id, int(first)) and vlr_db.match_stats_exist(self.player_id, int(last))
    
    def to_dict(self) -> dict:
        return {
            "player-id": self.player_id,
            "display-name": self.display_name,
            "real-name": self.real_name,
            "role": self.role
        }

class Team(Base):
    __tablename__ = "teams"
    team_id: Mapped[int] = mapped_column(primary_key=True)
    display_name: Mapped[str] = mapped_column()
    display_tag: Mapped[str] = mapped_column()
    players: Mapped[List[Player]] = relationship()

    def url(self) -> str:
        return f"https://www.vlr.gg/team/{self.team_id}"
    
    def to_dict(self):
        return {
            "team-id": self.team_id,
            "team_name": self.display_name,
            "display-tag": self.display_tag,
            "players" : [p.to_dict() for p in self.players]
        }

class Match(Base):
    __tablename__ = "matches"
    match_id: Mapped[int] = mapped_column(primary_key=True)
    event_name: Mapped[str] = mapped_column()
    match_name: Mapped[str] = mapped_column()
    match_timestamp: Mapped[int]


class MatchStats(Base):
    __tablename__ = "match_stats"
    player_id: Mapped[int] = mapped_column(db.ForeignKey("players.player_id"), primary_key=True)
    match_id: Mapped[int] = mapped_column(db.ForeignKey("matches.match_id"), primary_key=True)
    rating: Mapped[float] = mapped_column()
    acs: Mapped[int] = mapped_column()
    kills: Mapped[int] = mapped_column()
    assists: Mapped[int] = mapped_column()
    deaths: Mapped[int] = mapped_column()
    kast: Mapped[str] = mapped_column()
    adr: Mapped[int] = mapped_column()
    hs: Mapped[str] = mapped_column()
    first_bloods: Mapped[int] = mapped_column()
    first_deaths: Mapped[int] = mapped_column()
    clutch_1v1s: Mapped[int] = mapped_column()
    clutch_1v2s: Mapped[int] = mapped_column()
    clutch_1v3s: Mapped[int] = mapped_column()
    clutch_1v4s: Mapped[int] = mapped_column()
    clutch_1v5s: Mapped[int] = mapped_column()
    multikill_3ks: Mapped[int] = mapped_column()
    multikill_4ks: Mapped[int] = mapped_column()
    multikill_5ks: Mapped[int] = mapped_column()
    plants: Mapped[int] = mapped_column()
    defuses: Mapped[int] = mapped_column()


class Database:
    def __init__(self):
        Base.metadata.create_all(engine)  # Creates the table
        Session = sessionmaker(bind=engine)
        self.session = Session()

    def add_team(self, name: str, tag: str, id: int):
        team = Team(team_id = id, display_name = name, display_tag = tag)
        self.session.add(team)
        self.session.commit()

    def add_player(self, p: Player) -> None:
        self.session.add(p)
        self.session.commit()

    def add_match_stats(self, m: MatchStats) -> None:
        self.session.add(m)
        self.session.commit()

    def all_teams(self):
        return self.session.query(Team).all()
    
    def all_players(self):
        return self.session.query(Player).all()
    
    def get_player(self, player_id: int) -> Player:
        return self.session.query(Player).filter(Player.player_id == player_id).first()

    def get_player_matches(self, player_id: int) -> List[MatchStats]:
        return self.session.query(MatchStats).filter(MatchStats.player_id == player_id).all()
    
    def get_player_stats(self, player_id: int, _from = 0, _to = time.time()) -> dict:
        stats = self.session.query(
            func.sum(MatchStats.kills),
            func.sum(MatchStats.assists),
            func.sum(MatchStats.deaths),
            func.sum(MatchStats.first_bloods),
            func.sum(MatchStats.first_deaths),
            func.sum(MatchStats.plants),
            func.sum(MatchStats.defuses),
            func.sum(MatchStats.clutch_1v1s),
            func.sum(MatchStats.clutch_1v2s),
            func.sum(MatchStats.clutch_1v3s),
            func.sum(MatchStats.clutch_1v4s),
            func.sum(MatchStats.clutch_1v5s),
            func.sum(MatchStats.multikill_3ks),
            func.sum(MatchStats.multikill_4ks),
            func.sum(MatchStats.multikill_5ks),
            func.sum(MatchStats.rating),
            func.count().filter(MatchStats.rating != 0.0)
        ).filter(MatchStats.player_id == player_id, MatchStats.match_epoch > _from, MatchStats.match_epoch < _to).first()

        return {
            "average-rating": "{:.2f}".format(stats[15] / stats[16]),
            "kills": stats[0],
            "assists": stats[1],
            "deaths": stats[2],
            "first-bloods": stats[3],
            "first-deaths": stats[4],
            "spike-plants": stats[5],
            "spike-defuses": stats[6],
            "clutches": {
                "1v1": stats[7],
                "1v2": stats[8],
                "1v3": stats[9],
                "1v4": stats[10],
                "1v5": stats[11]
            },
            "multikills": {
                "3k": stats[12],  
                "4k": stats[13],  
                "5k": stats[14],  
            },
        }
    

    def match_stats_exist(self, player_id: int, epoch: int) -> bool:
        #print(f"[INFO] Checking stats for player {player_id} at epoch {epoch}")
        return self.session.query(MatchStats).filter(MatchStats.player_id == player_id, MatchStats.match_epoch == epoch).first() != None

    def __get_player_match_parsed(self, player_id: int) -> tuple[int]:
        return self.session.query(func.max(MatchStats.match_epoch), func.min(MatchStats.match_epoch)).filter(MatchStats.player_id == player_id).all()

    def __update_player_stats(self, player: Player):
        end_timestamp = vlr_scraper.get_end_timestamps(player.player_id)[1]
        for m in vlr_scraper.scrape_player_matches(player):
            if self.match_stats_exist(player.player_id, m['timestamp']):
                print("Skipped match")
                if vlr_db.match_stats_exist(player.player_id, end_timestamp):
                    print(f"Completed {player.display_name}")
                    return
                continue
            print(f"Found match: {m['match-name']}")
            match = MatchStats(
                player_id = player.player_id,
                match_epoch = int(m['timestamp']),
                match_name = m['match-name'],
                rating = m['rating'],
                acs = m['acs'],
                kast = m['KAST'],
                adr = m['ADR'],
                hs = m['HS'],
                kills = m['kills'],
                assists = m['assists'],
                deaths = m['deaths'],
                first_bloods = m['first-bloods'],
                first_deaths = m['first-deaths'],
                clutch_1v1s = m['clutches']["1v1"],
                clutch_1v2s = m['clutches']["1v2"],
                clutch_1v3s = m['clutches']["1v3"],
                clutch_1v4s = m['clutches']["1v4"],
                clutch_1v5s = m['clutches']["1v5"],
                multikill_3ks = m['multikills']['3k'],
                multikill_4ks = m['multikills']['4k'],
                multikill_5ks = m['multikills']['5k'],
                plants =  m['spike-plants'],
                defuses = m['spike-defuses']
            )
            vlr_db.add_match_stats(match)
    
    def get_unique_match_urls(self) -> list:
        all_urls = set()
        for player in self.all_players():
            print(f"Getting urls for: {player.display_name}")
            all_urls.update(vlr_scraper.get_match_urls(player.player_id))
        with open("matches.txt", "w+", encoding='utf-8') as f:
            f.write('\n'.join(all_urls))
        return all_urls

    def populate_initial_data(self):
        all_urls = []
        with open("matches.txt", "r", encoding='utf-8') as f:
            all_urls = list(set(f.read().split("\n")))
        
        for url in all_urls:
            print(url)
            match_data = vlr_scraper.scrape_match(url)


    def update_player_stats(self):
        for team in self.all_teams():
            for player in team.players:
                if player.role != "coach" and not player.is_complete():
                    print(f"Scraping {player.display_name}")
                    self.__update_player_stats(player)
                else:
                    print(f"[INFO] Skipped {player.display_name}")


vlr_db = Database()

if __name__ == "__main__":
    #vlr_db.update_player_stats()
    vlr_db.populate_initial_data()
                
