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

import os, logging
from faker import Faker
from faker.providers import DynamicProvider

import sqlalchemy

from connect_tcp import connect_tcp_socket

logger = logging.getLogger()

adjective = DynamicProvider(
     provider_name="adjective",
     elements=["the Merciless", "the Humble", "the Wise", "the Valiant", "the Swift", "the Just", "the Cunning", "the Steadfast",
    "the Bold", "the Unseen", "the Radiant", "the Enduring", "the Fierce", "the Benevolent", "the Tempestuous", "the Vigilant",
    "the Ironclad", "the Unbound", "the Resolute", "the Astute", "the Dire", "the Unfortunate", "the Glutton", "the Sad"]
)

fake = Faker()

# then add new provider to faker instance
fake.add_provider(adjective)

def init_connection_pool() -> sqlalchemy.engine.base.Engine:
    # use a TCP socket when INSTANCE_HOST (e.g. 127.0.0.1) is defined
    if os.environ.get("INSTANCE_HOST"):
        return connect_tcp_socket()

    raise ValueError(
        "Missing database connection parameter. Please define INSTANCE_HOST"
    )

def migrate_db(db: sqlalchemy.engine.base.Engine) -> None:
    with db.connect() as conn:
        insert_stmt = sqlalchemy.text("INSERT INTO players (player_name) VALUES (:player)")

        for _ in range(0, 1000):
            p_name = fake.first_name()+", "+fake.adjective()
            print(p_name)
            try:
                conn.execute(insert_stmt, player=p_name)
            except Exception as e:
                logger.exception(e)


# initiate a connection pool to the AlloyDB database
db = init_connection_pool()

# creates required 'players' table in database (if it does not exist)
# loads initial players if not there already
migrate_db(db)
