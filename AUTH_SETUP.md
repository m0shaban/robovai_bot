# 🔐 Authentication System Setup Guide

## Overview
RoboVAI Bot now includes a professional SaaS authentication system with:
- ✅ Multi-tenant support
- ✅ Role-based access control (RBAC)
- ✅ JWT tokens (access + refresh)
- ✅ Password reset flow
- ✅ Email verification
- ✅ Modern glassmorphism UI

## Quick Start

### 1. Run Database Migration
```powershell
python -m alembic upgrade head
```

### 2. Create Super Admin Account
```powershell
python scripts/create_super_admin.py
```

Follow the prompts to enter:
- Email address
- Full name
- Password (min 8 characters)

### 3. Start the Application
```powershell
python run.ps1
```

### 4. Access Authentication Pages

- **Register**: `http://localhost:8000/ui/auth/register`
- **Login**: `http://localhost:8000/ui/auth/login`
- **Forgot Password**: `http://localhost:8000/ui/auth/forgot-password`

## User Roles

| Role | Permissions |
|------|------------|
| `super_admin` | Full system access, manage all tenants |
| `admin` | Full access to their tenant |
| `manager` | Manage team and settings |
| `agent` | Handle chats and leads |
| `viewer` | Read-only access |

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login user
- `POST /api/v1/auth/refresh` - Refresh access token
- `POST /api/v1/auth/password/forgot` - Request password reset
- `POST /api/v1/auth/password/reset` - Reset password with token
- `GET /api/v1/auth/me` - Get current user profile
- `PATCH /api/v1/auth/me` - Update user profile
- `POST /api/v1/auth/me/password` - Change password

### User Management (Admin only)
- `GET /api/v1/auth/users` - List users
- `POST /api/v1/auth/users` - Create user
- `GET /api/v1/auth/users/{id}` - Get user details
- `PATCH /api/v1/auth/users/{id}` - Update user
- `DELETE /api/v1/auth/users/{id}` - Delete user

## JWT Configuration

Edit `app/core/config.py` to customize:

```python
# Token expiration
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # Default: 30 minutes
REFRESH_TOKEN_EXPIRE_DAYS = 7     # Default: 7 days
REFRESH_TOKEN_REMEMBER_ME_DAYS = 30  # With remember_me: 30 days

# Secret key (change in production!)
SECRET_KEY = "your-secret-key-here"
```

## Security Features

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

## Multi-Tenant Architecture

Users belong to tenants via `tenant_id` foreign key:
- Super admins have `tenant_id = NULL` (access all tenants)
- Regular users are scoped to their tenant
- Tenant admins manage users within their tenant

## Troubleshooting

### Migration Issues
```powershell
# Check current migration version
python -m alembic current

# View migration history
python -m alembic history

# Rollback one version
python -m alembic downgrade -1
```

### Password Too Long Error
Passwords are automatically truncated to 72 bytes (bcrypt limit). This is handled internally - no action needed.

### Email Already Exists
Each email can only be used once. Use the forgot password flow to recover existing accounts.

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

## Next Steps

- [ ] Configure email service for verification/reset
- [ ] Add OAuth providers (Google, GitHub, etc.)
- [ ] Implement two-factor authentication
- [ ] Add session management dashboard
- [ ] Set up rate limiting for auth endpoints

## Support

For issues or questions:
- GitHub: https://github.com/m0shaban/robovai_bot
- Email: Buy Me a Coffee support links in the app

---
**Version**: 1.0  
**Last Updated**: December 14, 2025
