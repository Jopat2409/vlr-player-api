from __future__ import annotations
import sqlalchemy as db
from sqlalchemy.orm import declarative_base, sessionmaker, mapped_column, relationship, Mapped

import valorant

metadata = db.MetaData()
Base = declarative_base(metadata=metadata)
engine = db.create_engine("sqlite:///db.sqlite")


player_team = db.Table(
    "player_teams",
    metadata,
    db.Column("team_id", db.ForeignKey("teams.team_id")),
    db.Column("player_id", db.ForeignKey("players.player_id")),
)


class Player(Base):
    __tablename__ = "players"
    player_id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(db.ForeignKey("teams.team_id"))
    display_name: Mapped[str] = mapped_column()
    real_name: Mapped[str] = mapped_column()
    role: Mapped[str] = mapped_column()

class Team(Base):
    __tablename__ = "teams"
    team_id: Mapped[int] = mapped_column(primary_key=True)
    display_name: Mapped[str] = mapped_column()
    display_tag: Mapped[str] = mapped_column()
    players: Mapped[Player] = relationship(secondary=player_team)

    def url(self) -> str:
        return f"https://www.vlr.gg/team/{self.team_id}"



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

    def all_teams(self):
        return self.session.query(Team).all()

vlr_db = Database()

if __name__ == "__main__":
    for team in vlr_db.all_teams():
        for member in valorant.scrape_players_from_team(team):
            team_member = Player(
                player_id = member['player-id'],
                team_id = team.team_id,
                display_name = member['display-name'],
                real_name = member['real-name'],
                role = member['role']
            )
            vlr_db.add_player(team_member)
