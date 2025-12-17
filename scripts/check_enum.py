import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import async_session_maker
from sqlalchemy import text


async def check():
    async with async_session_maker() as s:
        r = await s.execute(
            text(
                "SELECT enumlabel FROM pg_enum WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'userrole')"
            )
        )
        values = [x[0] for x in r]
        print("Enum values in database:", values)


asyncio.run(check())
