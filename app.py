from flask import Flask, jsonify, request
import valorant

app = Flask(__name__)
valorant.init()

@app.route('/teams')
def get_teams():
    return jsonify(valorant.get_teams())

@app.route('/team/<id>')
def get_team(id):
    return jsonify(valorant.team_from_id(int(id)))

@app.route('/player/<id>')
def get_player(id):
    return jsonify(valorant.player_stats_from_id(int(id), 0))
