from flask import Flask, jsonify, request
import valorant

app = Flask(__name__)
valorant.load_data()

@app.route('/teams')
def get_teams():
    return jsonify(valorant.STATIC_DAT["tier1"]["teams"])

@app.route('/team/<id>')
def get_team(id):
    data = valorant.team_from_id(int(id))
    data.update({"players": valorant.players_from_team(int(id))})
    return jsonify(data)

@app.route('/player/<id>')
def get_player(id):
    return jsonify(valorant.player_from_id(int(id)))
