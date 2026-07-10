"""Сборка всех роутеров хендлеров."""

from aiogram import Router

from handlers import generate, library, onboarding, postprocess, presets, settings, start, variants, wizard


def setup_routers() -> Router:
    root = Router(name="root")
    root.include_router(start.router)
    root.include_router(onboarding.router)
    root.include_router(presets.router)
    root.include_router(wizard.router)
    root.include_router(library.router)
    root.include_router(variants.router)
    root.include_router(generate.router)
    root.include_router(postprocess.router)
    root.include_router(settings.router)
    return root
