from flask import Flask, jsonify, request
import time
import data

app = Flask(__name__)

@app.route('/teams')
def get_teams():
    return jsonify([t.to_dict() for t in data.vlr_db.all_teams()])

@app.route('/team/<id>')
def get_team(id):
    return jsonify(valorant.team_from_id(int(id)))

@app.route('/player/<id>')
def get_player(id):
    return jsonify(data.vlr_db.get_player(id).to_dict())

@app.route('/player/<id>/stats')
def get_player_stats(id):
    _from = request.args.get("from", 0, type=int)
    _to = request.args.get("to", time.time(), type=int)
    return jsonify(data.vlr_db.get_player_stats(id, _from, _to))
