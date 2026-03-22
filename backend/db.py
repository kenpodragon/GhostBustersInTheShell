"""Database connection pooling with fail-fast pattern."""
import psycopg2
import psycopg2.pool
import psycopg2.extras
from contextlib import contextmanager
from config import config

_pool = None


def init_pool():
    global _pool
    _pool = psycopg2.pool.ThreadedConnectionPool(
        minconn=2,
        maxconn=10,
        host=config.DB_HOST,
        port=config.DB_PORT,
        dbname=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
    )
    print(f"[DB] Pool initialized: {config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}")


@contextmanager
def get_conn():
    conn = _pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _pool.putconn(conn)


@contextmanager
def get_cursor(cursor_factory=None):
    factory = cursor_factory or psycopg2.extras.RealDictCursor
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=factory)
        try:
            yield cur
        finally:
            cur.close()


def query_one(sql, params=None):
    with get_cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def query_all(sql, params=None):
    with get_cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def execute(sql, params=None):
    with get_cursor() as cur:
        cur.execute(sql, params)
        return cur.rowcount
