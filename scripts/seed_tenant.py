from __future__ import annotations

import argparse
import secrets

from sqlalchemy import select

from app.db.session import async_session_maker
from app.models.tenant import Tenant


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Seed a Tenant into the database")
    p.add_argument("--name", required=True)
    p.add_argument("--api-key", default="")
    p.add_argument("--system-prompt", default="")
    p.add_argument("--webhook-url", default="")
    return p.parse_args()


async def main() -> None:
    args = _parse_args()

    api_key = args.api_key.strip() or secrets.token_urlsafe(24)
    system_prompt = args.system_prompt.strip() or None
    webhook_url = args.webhook_url.strip() or None

    async with async_session_maker() as session:
        existing = await session.execute(
            select(Tenant).where(Tenant.api_key == api_key)
        )
        if existing.scalar_one_or_none() is not None:
            raise SystemExit("api_key already exists")

        tenant = Tenant(
            name=args.name.strip(),
            api_key=api_key,
            system_prompt=system_prompt,
            webhook_url=webhook_url,
            branding_config={},
        )
        session.add(tenant)
        await session.commit()
        await session.refresh(tenant)

    print("Tenant created")
    print(f"tenant_id={tenant.id}")
    print(f"tenant_api_key={tenant.api_key}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
