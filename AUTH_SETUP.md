# 🔐 دليل إعداد نظام المصادقة والتفعيل - RoboVAI

## 📋 نظرة عامة

يدعم نظام RoboVAI نظام مصادقة متكامل يشمل:
- ✅ تسجيل مستخدمين جدد مع تفعيل البريد الإلكتروني
- ✅ تسجيل الدخول مع JWT tokens
- ✅ إعادة تعيين كلمة المرور عبر البريد
- ✅ دعم Gmail SMTP و SendGrid
- ✅ نظام صلاحيات متعدد المستويات (RBAC)
- ✅ Multi-tenant architecture

---

## 📧 إعداد البريد الإلكتروني (Gmail SMTP)

### الخطوة 1: تفعيل التحقق بخطوتين في Gmail

1. افتح [إعدادات أمان Google](https://myaccount.google.com/security)
2. فعّل **"التحقق بخطوتين"** (2-Step Verification)
3. أكمل عملية التفعيل

### الخطوة 2: إنشاء كلمة مرور التطبيق

1. افتح [كلمات مرور التطبيقات](https://myaccount.google.com/apppasswords)
2. اختر "أخرى (اسم مخصص)"
3. أدخل اسم مثل "RoboVAI"
4. انسخ كلمة المرور المكونة من 16 حرفاً

### الخطوة 3: إعداد ملف .env

انسخ `.env.example` إلى `.env` وأضف هذه الإعدادات:

```env
# Gmail SMTP Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx  # كلمة مرور التطبيق (16 حرف)
SMTP_TLS=true
EMAIL_FROM=your-email@gmail.com
EMAIL_FROM_NAME=RoboVAI

# Base URL (مهم لروابط التفعيل)
BASE_URL=http://localhost:8000  # أو رابط الإنتاج

# Security
SECRET_KEY=your-super-secret-random-key-here
```

### الخطوة 4: اختبار الإعدادات

```bash
python scripts/test_email.py --to your-email@example.com
```

أو اختبار جميع أنواع الرسائل:

```bash
python scripts/test_email.py --to your-email@example.com --all
```

---

## 🔧 خيارات البريد الإلكتروني الأخرى

### Gmail مع SSL (منفذ 465)

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
SMTP_SSL=true
SMTP_TLS=false
```

### SendGrid API (للإرسال بكميات كبيرة)

```env
SENDGRID_API_KEY=SG.your-api-key-here
EMAIL_FROM=noreply@yourdomain.com
EMAIL_FROM_NAME=RoboVAI
```

### Outlook / Office 365

```env
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USER=your-email@outlook.com
SMTP_PASSWORD=your-password
SMTP_TLS=true
```

### Amazon SES

```env
SMTP_HOST=email-smtp.us-east-1.amazonaws.com
SMTP_PORT=587
SMTP_USER=your-ses-smtp-username
SMTP_PASSWORD=your-ses-smtp-password
SMTP_TLS=true
```

---

## 🚀 Quick Start

### 1. Run Database Migration

```powershell
python -m alembic upgrade head
```

### 2. Create Super Admin Account

```powershell
python scripts/create_super_admin.py
```

### 3. Start the Application

```powershell
python start.py
```

### 4. Access Authentication Pages

- **Register**: `http://localhost:8000/ui/auth/register`
- **Login**: `http://localhost:8000/ui/auth/login`
- **Forgot Password**: `http://localhost:8000/ui/auth/forgot-password`

---

## 🔑 نظام المصادقة API

### التسجيل الجديد

```
POST /api/v1/auth/register
{
    "email": "user@example.com",
    "password": "SecurePass123",
    "full_name": "اسم المستخدم",
    "phone": "+966500000000"  // اختياري
}
```

### تسجيل الدخول

```
POST /api/v1/auth/login
{
    "email": "user@example.com",
    "password": "SecurePass123",
    "remember_me": false
}
```

### تفعيل البريد الإلكتروني

```
POST /api/v1/auth/verify-email
{
    "token": "verification-token-from-email"
}
```

### إعادة إرسال رابط التفعيل

```
POST /api/v1/auth/resend-verification
{
    "email": "user@example.com"
}
```

### إعادة تعيين كلمة المرور

```
# طلب إعادة التعيين
POST /api/v1/auth/password/forgot
{
    "email": "user@example.com"
}

# تأكيد إعادة التعيين
POST /api/v1/auth/password/reset
{
    "token": "reset-token-from-email",
    "new_password": "NewSecurePass123"
}
```

### تجديد التوكن

```
POST /api/v1/auth/refresh
{
    "refresh_token": "..."
}
```

### الحصول على الملف الشخصي

```
GET /api/v1/auth/me
Headers: Authorization: Bearer <access_token>
```

### اختبار إعدادات البريد (للمديرين)

```
GET /api/v1/auth/email/config-status

POST /api/v1/auth/email/test?token=admin-token&to_email=test@example.com
```

---

## 👥 User Management (Admin only)

- `GET /api/v1/auth/users` - List users
- `POST /api/v1/auth/users` - Create user
- `GET /api/v1/auth/users/{id}` - Get user details
- `PATCH /api/v1/auth/users/{id}` - Update user
- `DELETE /api/v1/auth/users/{id}` - Delete user

---

## 🔒 مستويات الصلاحيات

| الدور | الصلاحيات |
|-------|----------|
| `super_admin` | كامل الصلاحيات - إدارة كل شيء |
| `admin` | إدارة المشروع الخاص |
| `manager` | إدارة الفريق والإعدادات |
| `agent` | معالجة المحادثات والعملاء |
| `viewer` | عرض فقط |

---

## 🔐 Security Features

### Password Requirements

- Minimum 8 characters
- Must contain: uppercase, lowercase, and digit
- Automatically truncated to 72 bytes for bcrypt

### Token Security

- JWT with HS256 algorithm
- Access tokens expire in 30 minutes
- Refresh tokens expire in 7-30 days
- Tokens include user_id, role, and tenant_id

### Password Hashing

- Uses bcrypt with automatic salt generation
- Secure against rainbow table attacks
- Handles UTF-8 passwords correctly

---

## 🐛 استكشاف الأخطاء

### خطأ: "Gmail Authentication failed"

**السبب:** استخدام كلمة مرور Gmail العادية بدلاً من كلمة مرور التطبيق.

**الحل:**
1. تأكد من تفعيل التحقق بخطوتين
2. أنشئ كلمة مرور تطبيق جديدة
3. استخدم كلمة المرور المكونة من 16 حرفاً

### خطأ: "Connection refused" أو "Timeout"

**السبب:** المنفذ محجوب أو الجدار الناري يمنع الاتصال.

**الحل:**
1. تأكد من أن المنفذ 587 أو 465 مفتوح
2. جرب استخدام SendGrid كبديل
3. تحقق من إعدادات الشبكة

### خطأ: "Verification link not working"

**السبب:** `BASE_URL` غير صحيح.

**الحل:**
```env
# للتطوير المحلي
BASE_URL=http://localhost:8000

# للإنتاج
BASE_URL=https://yourdomain.com
```

### البريد يصل إلى Spam

**الحل:**
1. أضف سجلات SPF و DKIM لنطاقك
2. استخدم خدمة بريد موثوقة مثل SendGrid
3. تأكد من أن EMAIL_FROM يطابق نطاقك

### Migration Issues

```powershell
# Check current migration version
python -m alembic current

# View migration history
python -m alembic history

# Rollback one version
python -m alembic downgrade -1
```

---

## 📝 ملاحظات هامة

1. **لا تستخدم كلمة مرور Gmail العادية** - يجب استخدام كلمة مرور التطبيق
2. **احفظ SECRET_KEY آمناً** - استخدم قيمة عشوائية قوية
3. **اختبر البريد قبل الإنتاج** - استخدم `scripts/test_email.py`
4. **راقب سجلات الأخطاء** - الأخطاء تُسجل في `logs/`

---

## 🚀 البدء السريع

```bash
# 1. انسخ ملف الإعدادات
cp .env.example .env

# 2. عدّل الإعدادات في .env

# 3. شغّل المايجريشن
python -m alembic upgrade head

# 4. أنشئ مدير النظام
python scripts/create_super_admin.py

# 5. اختبر البريد
python scripts/test_email.py --to your-email@example.com

# 6. شغّل التطبيق
python start.py
```

---

## Development Notes

### Adding New Roles

1. Edit `app/models/user.py` - Update `UserRole` enum
2. Create migration: `python -m alembic revision --autogenerate -m "Add new role"`
3. Run migration: `python -m alembic upgrade head`

### Customizing UI

Templates are in `app/templates/auth/`:

- `register.html` - Registration form
- `login.html` - Login form
- `forgot_password.html` - Password reset request
- `reset_password.html` - Password reset confirmation
- `verify_email.html` - Email verification result

---

**Version**: 2.0  
**Last Updated**: December 17, 2025

© 2025 RoboVAI Solutions
