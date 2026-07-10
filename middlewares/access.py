"""Ограничение доступа по ALLOWED_USER_IDS."""

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, User

from config import settings
from texts import messages

logger = logging.getLogger("jinglelab.middleware.access")


class AccessMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not settings.access_restricted:
            return await handler(event, data)

        user: User | None = data.get("event_from_user")
        if user is not None and user.id in settings.allowed_user_ids:
            return await handler(event, data)

        if user is not None:
            logger.info("Доступ запрещён user_id=%s", user.id)

        if isinstance(event, Message):
            await event.answer(messages.ACCESS_DENIED)
        elif isinstance(event, CallbackQuery):
            await event.answer(messages.ACCESS_DENIED, show_alert=True)

        return None
