from __future__ import annotations

from typing import Any

import httpx


async def send_telegram_message(
    *,
    bot_token: str,
    chat_id: int,
    text: str,
    reply_keyboard_buttons: list[str] | None = None,
) -> None:
    if not bot_token:
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload: dict[str, Any] = {"chat_id": chat_id, "text": text}

    # Use ReplyKeyboardMarkup so clicking sends a normal text message (no callback handling needed).
    if reply_keyboard_buttons:
        keyboard = [[{"text": b}] for b in reply_keyboard_buttons if b]
        if keyboard:
            payload["reply_markup"] = {
                "keyboard": keyboard,
                "resize_keyboard": True,
                "one_time_keyboard": False,
                "selective": False,
            }

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
