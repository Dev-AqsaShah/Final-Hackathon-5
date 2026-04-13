"""
Database initialization script - Railway deploy ke baad ek baar chalao
Usage: python -m production.database.init_db
"""
import asyncio
import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

async def init():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        # manually build from parts
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        user = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "password")
        db = os.getenv("POSTGRES_DB", "fte_db")
        db_url = f"postgresql://{user}:{password}@{host}:{port}/{db}"

    print(f"Connecting to database...")
    conn = await asyncpg.connect(db_url)

    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path, "r") as f:
        schema_sql = f.read()

    await conn.execute(schema_sql)
    await conn.close()
    print("Database initialized successfully!")

if __name__ == "__main__":
    asyncio.run(init())
