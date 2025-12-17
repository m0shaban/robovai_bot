"""
Script to create the initial super admin user.
Run this after database migration to set up the first admin account.

Usage:
    python scripts/create_super_admin.py
"""

import asyncio
import sys
import os
import getpass

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import async_session_maker
from app.crud.user import create_super_admin, get_user_by_email, count_super_admins
from app.models.user import UserRole


async def main():
    print("\n" + "=" * 60)
    print("🚀 RoboVAI - Create Super Admin Account")
    print("=" * 60 + "\n")

    async with async_session_maker() as session:
        # Check if super admin already exists
        existing_count = await count_super_admins(session)
        if existing_count > 0:
            print(
                f"⚠️  {existing_count} super admin account(s) already exist in the system"
            )
            confirm = input("Create another super admin? (y/n): ").strip().lower()
            if confirm != "y":
                print("Cancelled.")
                return

        print("📝 Enter super admin account details:\n")

        # Get email
        while True:
            email = input("Email: ").strip()
            if not email or "@" not in email:
                print("❌ Please enter a valid email address")
                continue

            # Check if email exists
            existing = await get_user_by_email(session, email)
            if existing:
                print("❌ Email already exists")
                continue
            break

        # Get name
        while True:
            full_name = input("Full Name: ").strip()
            if not full_name or len(full_name) < 2:
                print("❌ Please enter a valid name (at least 2 characters)")
                continue
            break

        # Get password (using getpass for security)
        while True:
            password = getpass.getpass("Password (min 8 characters): ").strip()
            if len(password) < 8:
                print("❌ Password must be at least 8 characters")
                continue

            confirm_password = getpass.getpass("Confirm Password: ").strip()
            if password != confirm_password:
                print("❌ Passwords do not match")
                continue
            break

        print("\n" + "-" * 40)
        print("📋 Summary:")
        print(f"   Email: {email}")
        print(f"   Name: {full_name}")
        print(f"   Role: Super Admin (System Administrator)")
        print("-" * 40 + "\n")

        confirm = input("Create account? (y/n): ").strip().lower()
        if confirm != "y":
            print("Cancelled.")
            return

        # Create super admin
        try:
            user = await create_super_admin(
                session,
                email=email,
                password=password,
                full_name=full_name,
            )

            print("\n" + "=" * 60)
            print("✅ Super Admin Account Created Successfully!")
            print("=" * 60)
            print(f"\n📧 Email: {user.email}")
            print(f"👤 Name: {user.full_name}")
            print(f"🔑 Role: {user.role.value}")
            print(f"🆔 ID: {user.id}")
            print("\n🌐 You can now login at:")
            print("   http://localhost:8000/ui/auth/login")
            print("\n" + "=" * 60 + "\n")

        except Exception as e:
            print(f"\n❌ Error creating account: {e}")
            import traceback

            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
