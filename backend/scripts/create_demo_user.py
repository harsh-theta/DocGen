import asyncio
from backend.core.database import SessionLocal
from backend.services.auth import create_user

async def main():
    async with SessionLocal() as db:
        user = await create_user(db, "demo", "pass")
        print(f"Created demo user: {user.username} (id={user.id})")

if __name__ == "__main__":
    asyncio.run(main()) 