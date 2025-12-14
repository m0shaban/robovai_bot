"""
Script to create the initial super admin user.
Run this after database migration to set up the first admin account.

Usage:
    python -m scripts.create_super_admin
"""
import asyncio
import sys

from app.db.session import async_session_maker
from app.crud.user import create_super_admin, get_user_by_email, count_super_admins
from app.models.user import UserRole


async def main():
    print("\n" + "="*60)
    print("🚀 RoboVAI - إنشاء حساب المدير الأول")
    print("="*60 + "\n")
    
    async with async_session_maker() as session:
        # Check if super admin already exists
        existing_count = await count_super_admins(session)
        if existing_count > 0:
            print(f"⚠️  يوجد بالفعل {existing_count} حساب(ات) مدير في النظام")
            confirm = input("هل تريد إنشاء حساب مدير إضافي؟ (y/n): ").strip().lower()
            if confirm != 'y':
                print("تم الإلغاء.")
                return
        
        print("📝 أدخل بيانات حساب المدير:\n")
        
        # Get email
        while True:
            email = input("البريد الإلكتروني: ").strip()
            if not email or '@' not in email:
                print("❌ يرجى إدخال بريد إلكتروني صحيح")
                continue
            
            # Check if email exists
            existing = await get_user_by_email(session, email)
            if existing:
                print("❌ البريد الإلكتروني مستخدم بالفعل")
                continue
            break
        
        # Get name
        while True:
            full_name = input("الاسم الكامل: ").strip()
            if not full_name or len(full_name) < 2:
                print("❌ يرجى إدخال اسم صحيح (حرفين على الأقل)")
                continue
            break
        
        # Get password
        while True:
            password = input("كلمة المرور (8 أحرف على الأقل): ").strip()
            if len(password) < 8:
                print("❌ كلمة المرور يجب أن تكون 8 أحرف على الأقل")
                continue
            
            confirm_password = input("تأكيد كلمة المرور: ").strip()
            if password != confirm_password:
                print("❌ كلمتا المرور غير متطابقتين")
                continue
            break
        
        print("\n" + "-"*40)
        print("📋 ملخص البيانات:")
        print(f"   البريد: {email}")
        print(f"   الاسم: {full_name}")
        print(f"   الدور: Super Admin (مدير النظام)")
        print("-"*40 + "\n")
        
        confirm = input("هل تريد إنشاء الحساب؟ (y/n): ").strip().lower()
        if confirm != 'y':
            print("تم الإلغاء.")
            return
        
        # Create super admin
        try:
            user = await create_super_admin(
                session,
                email=email,
                password=password,
                full_name=full_name,
            )
            
            print("\n" + "="*60)
            print("✅ تم إنشاء حساب المدير بنجاح!")
            print("="*60)
            print(f"\n📧 البريد الإلكتروني: {user.email}")
            print(f"👤 الاسم: {user.full_name}")
            print(f"🔑 الدور: {user.role.value}")
            print(f"🆔 ID: {user.id}")
            print("\n🌐 يمكنك الآن تسجيل الدخول من:")
            print("   /ui/auth/login")
            print("\n" + "="*60 + "\n")
            
        except Exception as e:
            print(f"\n❌ خطأ في إنشاء الحساب: {e}")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
