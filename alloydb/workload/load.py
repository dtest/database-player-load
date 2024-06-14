# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    https:#www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Emulate authentication server workload"""

import json, os, random, requests

from locust import HttpUser, task, events

from flask import Blueprint, make_response, redirect, request, session, url_for
from flask_login import UserMixin, login_user

class MatchLoad(HttpUser):
    """
    Generate load by adding assigning matches and winners
    """

    # Stores a list of players that are not actively playing a match
    inactive_players = []

    def on_start(self):
        """When starting load generator, initialize players"""
        self.get_players()

    def get_players(self):
        """Initialize list of players from endpoint"""
        headers = {"Content-Type": "application/json"}
        req = requests.get(f"{self.host}/players", headers=headers, timeout=10)
        self.inactive_players = json.loads(req.text)


    @task
    def play_match(self):
        """Task to play a 1v1 match"""

        match_players = random.sample(self.inactive_players, 2)

        # match result: random number between 1-3
        match_result = random.randrange(1,100)%3+1

        # Submit the match to the alloydb_app
        headers = {"Content-Type": "application/json"}
        data = {"player1_id": match_players[0],
                "player2_id": match_players[1],
                "match_result": match_result}

        self.client.put("/match", data=json.dumps(data), headers=headers)

    @task(2)
    def get_player(self):
        """Task to get a player by their id"""

        headers = {"Content-Type": "application/json"}
        player_id = random.choice(self.inactive_players)
        self.client.get(f"/players/{player_id}", headers=headers, name="/players/[player_id]")

class AuthUser(UserMixin):
    def __init__(self, username):
        self.username = username

    def get_id(self):
        return self.username


auth_blueprint = Blueprint("auth", "web_ui_auth")


def load_user(user_id):
    return AuthUser(session.get("username"))


@events.init.add_listener
def locust_init(environment, **kwargs):
    if environment.web_ui:
        environment.web_ui.login_manager.user_loader(load_user)

        environment.web_ui.app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY")

        environment.web_ui.auth_args = {
            "username_password_callback": "/login_submit",
        }

        @auth_blueprint.route("/login_submit")
        def login_submit():
            username = request.args.get("username")
            password = request.args.get("password")

            # Implement real password verification here
            if username=='alloydb_next24' and password=='googlenext24!':
                session["username"] = username
                login_user(AuthUser(username))

                return redirect(url_for("index"))

            environment.web_ui.auth_args = {**environment.web_ui.auth_args, "error": "Invalid username or password"}

            return redirect(url_for("login"))

        environment.web_ui.app.register_blueprint(auth_blueprint)
