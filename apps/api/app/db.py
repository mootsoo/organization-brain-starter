import os
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://organization_brain:organization_brain@localhost:5432/organization_brain",
)


@contextmanager
def connection():
    """Open a short-lived PostgreSQL connection with dictionary rows."""
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        yield conn
