# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import logging
import os
from typing import Dict

from flask import Flask, render_template, request, Response

import sqlalchemy

from connect_tcp import connect_tcp_socket

app = Flask(__name__)

logger = logging.getLogger()


def init_connection_pool() -> sqlalchemy.engine.base.Engine:
    # use a TCP socket when INSTANCE_HOST (e.g. 127.0.0.1) is defined
    if os.environ.get("INSTANCE_HOST"):
        return connect_tcp_socket()

    raise ValueError(
        "Missing database connection parameter. Please define INSTANCE_HOST"
    )


# create tables in database if they don't already exist
# load players if not already done
def migrate_db(db: sqlalchemy.engine.base.Engine) -> None:
    with db.connect() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS players (
                player_id SERIAL NOT NULL,
                player_name VARCHAR(36) NOT NULL,
                created TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                updated TIMESTAMPTZ,
                matches_won integer DEFAULT 0,
                matches_lost integer DEFAULT 0,
                matches_tied integer DEFAULT 0,
                matches_played integer GENERATED ALWAYS AS (matches_won+matches_lost+matches_tied) STORED,
                score integer GENERATED ALWAYS AS (matches_won*2+matches_tied) STORED,
                PRIMARY KEY(player_id),
                UNIQUE (player_name)
            );
            CREATE TABLE IF NOT EXISTS matches (
                match_id SERIAL NOT NULL,
                player1_id integer REFERENCES players (player_id),
                player2_id integer REFERENCES players (player_id),
                match_result smallint NOT NULL,
                created TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(match_id),
                CHECK (match_result IN (1,2,3))
            );
            comment on column matches.match_result is '1# player1 won, 2# player2 won, 3# tie';
            CREATE INDEX IF NOT EXISTS created_idx ON matches (created);

            """
        )

        player_count = conn.execute(sqlalchemy.text("select count(*) from players")).fetchone()
        logger.debug("Existing players: '{player_count[0]}'")

        if (player_count[0] == 0):
            add_players(conn)

def add_players(conn) -> None:
    player_names = [
        "Aella, the Steadfast", "Cassia, the Untamed", "Cyrus, the Stormbringer", "Elara, the Dawnbringer",
        "Felix, the Fabled", "Gideon, the Unyielding", "Hadrian, the Wallbuilder", "Iris, the Weaver of Dreams",
        "Jaxon, the Ironscale", "Kallista, the Huntress", "Lysander, the Cunning", "Mara, the Voice of Thunder",
        "Nero, the Shadow", "Octavia, the Indomitable", "Petal, the Whisperer", "Quintus, the Eagle-Eyed",
        "Rhea, the Tidemother", "Sabina, the Savage", "Titus, the Last Stand", "Ulysses, the Wanderer",
        "Anya, of the Whispering Woods", "Bjorn, the Mountain-Breaker", "Caoimhe, the Weaver of Fate", "Darius, the Sun-King",
        "Elara, the Moonlit", "Finn, the Seafarer", "Griselda, the Alchemist", "Hector, the Lionhearted",
        "Indigo, the Shadow Dancer", "Jace, the Stormrider", "Kallista, the Flame-haired", "Lyra, the Songstress",
        "Marius, the Stonewall", "Nova, the Stargazer", "Octavia, the Unyielding", "Peregrine, the Falcon",
        "Quintus, the Navigator", "Rhea, the Wild Huntress", "Sabina, the Silver-tongued", "Titus, the Serpent",
        "Alistair, of the Northern Wastes", "Brielle, the Fierce", "Cassian, the Skyborn", "Dara, the Unbroken",
        "Elara, the Gale", "Finnian, the Bard", "Gwendolyn, the Dragonslayer", "Hector, the Thunderous",
        "Isla, the Weaver of Illusions", "Jax, the Howling Wind", "Kallista, the Emerald-Eyed", "Leyla, the Night Dancer",
        "Marcus, the Steadfast", "Nova, the Star-Forged", "Octavia, the Falconer", "Peregrine, the Silent",
        "Quintus, the Scholar", "Rhea, the Storm’s Fury", "Sabina, the Blade Singer", "Titus, the Redeemer"
    ]

    logger.debug("Inserting %d players", len(player_names))

    insert_stmt = sqlalchemy.text("INSERT INTO players (player_name) VALUES (:player)")

    for p_name in player_names:
        try:
            conn.execute(insert_stmt, player=p_name)
        except Exception as e:
            logger.exception(e)


# This global variable is declared with a value of `None`, instead of calling
# `init_db()` immediately, to simplify testing. In general, it
# is safe to initialize your database connection pool when your script starts
# -- there is no need to wait for the first request.
db = None


# init_db lazily instantiates a database connection pool. Users of Cloud Run or
# App Engine may wish to skip this lazy instantiation and connect as soon
# as the function is loaded. This is primarily to help testing.
@app.before_request
def init_db() -> sqlalchemy.engine.base.Engine:
    global db
    if db is None:
        db = init_connection_pool()
        migrate_db(db)

# Index route, renders leaderboard from template
@app.route("/", methods=["GET"])
def render_index() -> str:
    context = get_index_context(db)
    return render_template("index.html", **context)

# Retrieve all players. Used by Locust to pre-fetch players for load test
# Don't do this in prod applications.
@app.route("/players", methods=["GET"])
def get_match_players() -> list:
    players = []

    # Get all players
    with db.connect() as conn:
        player_results = conn.execute(
            "SELECT player_id FROM players"
        ).fetchall()

        for row in player_results:
            players.append(row[0])

    return players

@app.route("/players/<player_id>", methods=["GET"])
def get_player_by_id(player_id) -> list:
    with db.connect() as conn:
        player_result = conn.execute(sqlalchemy.text(
            "SELECT player_name, score, matches_played, matches_won, matches_tied, matches_lost, created, updated"
            " FROM players WHERE player_id=:p_id"
        ), p_id=player_id).fetchone()

    return dict(player_result)

# Record match results via a PUT request
@app.route("/match", methods=["PUT"])
def save_match_results() -> Response:
    match_results = request.get_json()
    return record_match(match_results)

# get_index_context gets data required for rendering HTML application
def get_index_context(db: sqlalchemy.engine.base.Engine) -> Dict:
    top_players = []

    with db.connect() as conn:
        # Execute the query and fetch all results
        player_results = conn.execute(
            "SELECT player_name, score, matches_played, matches_won, matches_tied, matches_lost FROM players"
            " ORDER BY score DESC LIMIT 10"
        ).fetchall()
        # Convert the results into a list of dicts representing votes
        for row in player_results:
            top_players.append({"player_name": row[0],
                                "player_stats": {
                                        "score": row[1],
                                        "matches_played": row[2],
                                        "matches_won": row[3],
                                        "matches_tied": row[4],
                                        "matches_lost": row[5]
                                    }
                                })

    return {
        "top_players": top_players,
    }

# update_stats saves player stats for players involved in a match
def record_match(match_result: dict) -> Response:
    update_ts = datetime.datetime.now(tz=datetime.timezone.utc)

    # Expected format of 'match_result': {'player1': '', 'player2': '', 'match_result': '(1|2|3)'}

    # Player 1 won
    if match_result['match_result'] == 1 :
        player1_stmt = sqlalchemy.text(
            "UPDATE players SET matches_won = matches_won + 1, matches_lost = matches_lost, updated=:update_ts "
            "WHERE player_id = :player_id"
        )

        player2_stmt = sqlalchemy.text(
            "UPDATE players SET matches_won = matches_won, matches_lost = matches_lost + 1, updated=:update_ts "
            "WHERE player_id = :player_id"
        )

    # Player 2 won
    elif match_result['match_result'] == 2 :
        player1_stmt = sqlalchemy.text(
            "UPDATE players SET matches_won = matches_won, matches_lost = matches_lost + 1, updated=:update_ts "
            "WHERE player_id = :player_id"
        )

        player2_stmt = sqlalchemy.text(
            "UPDATE players SET matches_won = matches_won + 1, matches_lost = matches_lost, updated=:update_ts "
            "WHERE player_id = :player_id"
        )

    # It was a tie
    else:
        player1_stmt = sqlalchemy.text(
            "UPDATE players SET matches_tied = matches_tied + 1, updated=:update_ts "
            "WHERE player_id = :player_id"
        )

        player2_stmt = sqlalchemy.text(
            "UPDATE players SET matches_tied = matches_tied + 1, updated=:update_ts "
            "WHERE player_id = :player_id"
        )

    try:
        # Transaction to record match
        with db.begin() as conn:
            # Record match results
            conn.execute(sqlalchemy.text(
                "INSERT INTO matches (player1_id, player2_id, match_result) VALUES"
                " (:player1_id, :player2_id, :match_result)"
            ), player1_id=match_result['player1_id'], player2_id=match_result['player2_id'], match_result=match_result['match_result'])

            # Update player 1
            conn.execute(player1_stmt, update_ts=update_ts, player_id=match_result['player1_id'])

            # Update player 2
            conn.execute(player2_stmt, update_ts=update_ts, player_id=match_result['player2_id'])

    except Exception as e:
        logger.exception(e)

    return Response(
        status=200,
        response=f"Updated player_stats for '{match_result['player1_id']}' v '{match_result['player2_id']}' at time {update_ts}!",
    )

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=True)
