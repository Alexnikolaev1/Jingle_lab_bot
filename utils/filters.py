"""Кастомные фильтры aiogram."""

from aiogram import F

from utils.keyboards import MENU_BUTTONS

# Свободный текст, не являющийся командой или кнопкой меню
FreeTextFilter = F.text & ~F.text.startswith("/") & ~F.text.in_(MENU_BUTTONS)
