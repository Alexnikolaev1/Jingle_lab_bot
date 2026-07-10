"""
bot.py — Точка входа JINGLE LAB AI.
"""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from config import settings
import database as db
from handlers import setup_routers
from middlewares import ErrorHandlerMiddleware, ThrottlingMiddleware, UserMiddleware
from utils.helpers import cleanup_old_tmp_files, ensure_tmp_dir
from utils.http_client import close_http_session
from utils.queue_service import generation_queue
from utils.redis_client import close_redis, get_redis

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("jinglelab.bot")

_health_runner: web.AppRunner | None = None


def _init_sentry() -> None:
    if not settings.SENTRY_DSN:
        return
    try:
        import sentry_sdk

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            traces_sample_rate=0.1,
            environment="production" if settings.USE_WEBHOOK else "development",
        )
        logger.info("Sentry инициализирован")
    except Exception:
        logger.exception("Не удалось инициализировать Sentry")


async def _create_storage():
    redis = await get_redis()
    if redis is not None:
        from aiogram.fsm.storage.redis import RedisStorage

        logger.info("FSM storage: Redis")
        return RedisStorage(redis=redis)
    logger.info("FSM storage: Memory")
    return MemoryStorage()


def create_dispatcher(storage) -> Dispatcher:
    dp = Dispatcher(storage=storage)
    dp.update.middleware(ErrorHandlerMiddleware())
    dp.update.middleware(UserMiddleware())
    dp.message.middleware(ThrottlingMiddleware(rate_limit=settings.THROTTLE_RATE_SECONDS))
    dp.callback_query.middleware(
        ThrottlingMiddleware(rate_limit=settings.THROTTLE_RATE_SECONDS)
    )
    dp.include_router(setup_routers())
    return dp


async def _periodic_tmp_cleanup() -> None:
    while True:
        try:
            removed = await asyncio.to_thread(cleanup_old_tmp_files)
            if removed:
                logger.info("Очистка /tmp: удалено файлов — %s", removed)
        except Exception:
            logger.exception("Ошибка при очистке временных файлов")
        await asyncio.sleep(600)


async def _on_startup(bot: Bot) -> None:
    global _health_runner
    ensure_tmp_dir()
    await db.init_db()
    generation_queue.start()
    asyncio.create_task(_periodic_tmp_cleanup())

    if settings.USE_WEBHOOK:
        await bot.set_webhook(
            url=settings.WEBHOOK_URL,
            drop_pending_updates=True,
        )
        logger.info("Вебхук установлен: %s", settings.WEBHOOK_URL)
    else:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Вебхук не настроен — используется long polling.")
        if settings.ENABLE_HEALTH_SERVER:
            app = web.Application()

            async def health_check(request: web.Request) -> web.Response:
                return web.json_response(
                    {
                        "status": "ok",
                        "service": "JINGLE LAB AI",
                        "mode": "polling",
                        "queue_size": generation_queue.size,
                    }
                )

            app.router.add_get("/", health_check)
            _health_runner = web.AppRunner(app)
            await _health_runner.setup()
            site = web.TCPSite(_health_runner, settings.HOST, settings.PORT)
            await site.start()
            logger.info("Health-сервер: http://%s:%s/", settings.HOST, settings.PORT)

    logger.info("JINGLE LAB AI запущен и готов к работе 🎧")


async def _on_shutdown(bot: Bot) -> None:
    global _health_runner
    logger.info("Остановка бота…")
    await generation_queue.stop()
    await close_http_session()
    await close_redis()
    if _health_runner is not None:
        await _health_runner.cleanup()
        _health_runner = None
    if settings.USE_WEBHOOK:
        await bot.delete_webhook()


def main() -> None:
    _init_sentry()

    async def _main_async() -> None:
        storage = await _create_storage()
        bot = Bot(
            token=settings.TELEGRAM_BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        dp = create_dispatcher(storage)
        dp.startup.register(_on_startup)
        dp.shutdown.register(_on_shutdown)

        if settings.USE_WEBHOOK:
            app = web.Application()
            SimpleRequestHandler(dispatcher=dp, bot=bot).register(
                app, path=settings.WEBHOOK_PATH
            )
            setup_application(app, dp, bot=bot)

            async def health_check(request: web.Request) -> web.Response:
                return web.json_response(
                    {
                        "status": "ok",
                        "service": "JINGLE LAB AI",
                        "queue_size": generation_queue.size,
                    }
                )

            app.router.add_get("/", health_check)
            web.run_app(app, host=settings.HOST, port=settings.PORT)
        else:
            await dp.start_polling(bot)

    asyncio.run(_main_async())


if __name__ == "__main__":
    main()
