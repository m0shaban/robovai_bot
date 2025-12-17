from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message_template import MessageTemplate, TemplateCategory


async def create_message_template(
    *,
    session: AsyncSession,
    tenant_id: int,
    name: str,
    category: str,
    content: str,
    variables: str | None = None,
) -> MessageTemplate:
    """Create a new message template"""
    try:
        cat = TemplateCategory(category)
    except ValueError:
        cat = TemplateCategory.general

    obj = MessageTemplate(
        tenant_id=tenant_id,
        name=name,
        category=cat,
        content=content,
        variables=variables,
        is_active=True,
    )
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


async def list_message_templates(
    *,
    session: AsyncSession,
    tenant_id: int,
    category: str | None = None,
    active_only: bool = True,
) -> list[MessageTemplate]:
    """List message templates for a tenant"""
    stmt = select(MessageTemplate).where(MessageTemplate.tenant_id == tenant_id)

    if category:
        try:
            cat = TemplateCategory(category)
            stmt = stmt.where(MessageTemplate.category == cat)
        except ValueError:
            pass

    if active_only:
        stmt = stmt.where(MessageTemplate.is_active == True)

    stmt = stmt.order_by(MessageTemplate.category, MessageTemplate.name)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_message_template_by_id(
    *,
    session: AsyncSession,
    template_id: int,
) -> MessageTemplate | None:
    """Get a message template by ID"""
    result = await session.execute(
        select(MessageTemplate).where(MessageTemplate.id == template_id)
    )
    return result.scalar_one_or_none()


async def update_message_template(
    *,
    session: AsyncSession,
    template_id: int,
    name: str | None = None,
    category: str | None = None,
    content: str | None = None,
    variables: str | None = None,
    is_active: bool | None = None,
) -> MessageTemplate | None:
    """Update a message template"""
    template = await get_message_template_by_id(
        session=session, template_id=template_id
    )
    if not template:
        return None

    if name is not None:
        template.name = name
    if category is not None:
        try:
            template.category = TemplateCategory(category)
        except ValueError:
            pass
    if content is not None:
        template.content = content
    if variables is not None:
        template.variables = variables
    if is_active is not None:
        template.is_active = is_active

    await session.commit()
    await session.refresh(template)
    return template


async def delete_message_template(
    *,
    session: AsyncSession,
    template_id: int,
) -> bool:
    """Delete a message template"""
    template = await get_message_template_by_id(
        session=session, template_id=template_id
    )
    if not template:
        return False

    await session.delete(template)
    await session.commit()
    return True


async def seed_default_templates(
    *,
    session: AsyncSession,
    tenant_id: int,
) -> list[MessageTemplate]:
    """Create default templates for a new tenant"""

    default_templates = [
        # ترحيب
        {
            "name": "ترحيب عام",
            "category": "welcome",
            "content": "أهلاً وسهلاً بك! 👋\nكيف يمكنني مساعدتك اليوم؟",
            "variables": None,
        },
        {
            "name": "ترحيب باسم العميل",
            "category": "welcome",
            "content": "مرحباً {customer_name}! 🌟\nسعيد بتواصلك معنا. كيف أقدر أساعدك؟",
            "variables": "customer_name",
        },
        # وداع
        {
            "name": "وداع إيجابي",
            "category": "farewell",
            "content": "شكراً لتواصلك معنا! 🙏\nنتمنى لك يوماً سعيداً. لا تتردد في التواصل معنا في أي وقت!",
            "variables": None,
        },
        # شكاوى
        {
            "name": "استلام شكوى",
            "category": "complaint",
            "content": "نعتذر جداً عن أي إزعاج واجهته 😔\nتم تسجيل شكواك وسيتم التعامل معها بأسرع وقت.\nرقم الشكوى: #{ticket_id}",
            "variables": "ticket_id",
        },
        {
            "name": "حل شكوى",
            "category": "complaint",
            "content": "تم حل المشكلة بنجاح! ✅\nنأمل أن تكون راضياً عن الحل. شكراً لصبرك وتفهمك.",
            "variables": None,
        },
        # استفسار
        {
            "name": "طلب توضيح",
            "category": "inquiry",
            "content": "شكراً لسؤالك! 🤔\nهل يمكنك توضيح المزيد من التفاصيل لأتمكن من مساعدتك بشكل أفضل؟",
            "variables": None,
        },
        # عروض
        {
            "name": "عرض خاص",
            "category": "promotion",
            "content": "🎉 عرض خاص لك!\n{offer_details}\nالعرض ساري حتى {end_date}\nلا تفوت الفرصة!",
            "variables": "offer_details,end_date",
        },
        # دعم فني
        {
            "name": "طلب معلومات تقنية",
            "category": "support",
            "content": "لأتمكن من مساعدتك في حل المشكلة التقنية، أرجو إرسال:\n• نوع الجهاز\n• نظام التشغيل\n• وصف المشكلة بالتفصيل",
            "variables": None,
        },
        {
            "name": "إحالة للدعم البشري",
            "category": "support",
            "content": "سأقوم بتحويلك لأحد موظفي الدعم المتخصصين 👨‍💻\nالرجاء الانتظار لحظات...",
            "variables": None,
        },
        # دفع
        {
            "name": "تأكيد دفع",
            "category": "payment",
            "content": "✅ تم استلام الدفع بنجاح!\nالمبلغ: {amount}\nرقم العملية: {transaction_id}\nشكراً لثقتك بنا!",
            "variables": "amount,transaction_id",
        },
        {
            "name": "تذكير بالدفع",
            "category": "payment",
            "content": "⏰ تذكير ودي\nلديك فاتورة مستحقة بمبلغ {amount}\nتاريخ الاستحقاق: {due_date}\nيرجى السداد لتجنب أي تأخير.",
            "variables": "amount,due_date",
        },
        # شحن
        {
            "name": "تأكيد الشحن",
            "category": "shipping",
            "content": "📦 تم شحن طلبك!\nرقم التتبع: {tracking_number}\nالوصول المتوقع: {delivery_date}\nيمكنك تتبع شحنتك من هنا: {tracking_link}",
            "variables": "tracking_number,delivery_date,tracking_link",
        },
        # عام
        {
            "name": "خارج أوقات العمل",
            "category": "general",
            "content": "شكراً لتواصلك! 🌙\nنحن حالياً خارج أوقات العمل.\nأوقات العمل: {working_hours}\nسنرد عليك في أقرب وقت!",
            "variables": "working_hours",
        },
    ]

    created = []
    for tmpl in default_templates:
        obj = await create_message_template(
            session=session,
            tenant_id=tenant_id,
            **tmpl,
        )
        created.append(obj)

    return created
