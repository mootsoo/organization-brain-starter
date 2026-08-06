import os
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://organization_brain:organization_brain@localhost:5432/organization_brain",
)

# Keep a bounded connect time so a database outage fails fast with a clear
# error instead of holding the API request open.
CONNECT_TIMEOUT_SECONDS = int(os.getenv("DB_CONNECT_TIMEOUT", "5"))


@contextmanager
def connection():
    """Open a short-lived PostgreSQL connection with dictionary rows."""
    with psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row,
        connect_timeout=CONNECT_TIMEOUT_SECONDS,
    ) as conn:
        yield conn
