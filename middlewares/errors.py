"""Глобальный перехват необработанных исключений в хендлерах."""

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

logger = logging.getLogger("jinglelab.middleware.errors")


class ErrorHandlerMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except Exception:
            logger.exception("Необработанная ошибка в хендлере")
            text = "❌ Произошла ошибка. Попробуй ещё раз или напиши /help."
            if isinstance(event, Message):
                await event.answer(text)
            elif isinstance(event, CallbackQuery):
                await event.answer("Ошибка", show_alert=True)
                if event.message:
                    await event.message.answer(text)
            return None
