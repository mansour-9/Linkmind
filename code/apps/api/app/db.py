import os

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, CursorResult

engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)


def sql(conn: Connection, statement: str, **params) -> CursorResult:
    return conn.execute(text(statement), params)
