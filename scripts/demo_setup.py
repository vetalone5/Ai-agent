"""Quick demo: create tables, seed data, start dashboard."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def setup():
    from src.db.session import engine
    from src.models import Base

    print("Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created.")

    print("Seeding keywords...")
    from scripts.seed_keywords import seed as seed_kw
    await seed_kw()

    print("Seeding competitors...")
    from scripts.seed_competitors import seed as seed_comp
    await seed_comp()

    print("\nReady! Start the dashboard with:")
    print("  PYTHONPATH=. uvicorn src.dashboard.app:app --host 0.0.0.0 --port 8000 --reload")


if __name__ == "__main__":
    asyncio.run(setup())
