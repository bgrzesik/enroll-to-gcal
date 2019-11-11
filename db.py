# Created by Bartłomiej Grzesik

import sqlite3


def get_db_connection():
    conn = sqlite3.connect("events.db")

    conn.execute("""
    CREATE TABLE IF NOT EXISTS events(
        event_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        start timestamp NOT NULL,
        end timestamp NOT NULL
    );
    """)
    conn.commit()

    return conn
