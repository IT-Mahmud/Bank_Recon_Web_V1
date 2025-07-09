# utils/db.py

from sqlalchemy import create_engine, inspect

MYSQL_USER = 'root'
MYSQL_PASSWORD = '%23lme11%40%40'
MYSQL_HOST = 'localhost'
MYSQL_DB = 'bank_reconciliation'

engine = create_engine(
    f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DB}'
)

def ensure_table_exists(engine, table_name):
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        raise Exception(
            f"Table '{table_name}' does not exist. Please create it manually in MySQL before uploading."
        )
