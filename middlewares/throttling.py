"""Простой антиспам: не более одного запроса в секунду на пользователя."""

import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from texts import messages


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: float = 1.0) -> None:
        self._rate_limit = rate_limit
        self._last_request: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user_id: int | None = None
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id

        if user_id is not None:
            now = time.monotonic()
            last = self._last_request.get(user_id, 0.0)
            if now - last < self._rate_limit:
                if isinstance(event, Message):
                    await event.answer(messages.THROTTLE)
                elif isinstance(event, CallbackQuery):
                    await event.answer(messages.THROTTLE, show_alert=True)
                return None
            self._last_request[user_id] = now

        return await handler(event, data)
