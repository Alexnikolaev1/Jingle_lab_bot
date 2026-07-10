# 🎧 JINGLE LAB AI

Telegram-бот — персональная AI-фабрика джинглов, аудиологотипов и звуковых
эффектов. Работает на бесплатных нейросетях (MusicGen, AudioLDM через
Hugging Face Inference API) и локальной постобработке через FFmpeg.

## Возможности

- 🎼 **Джинглы и интро** — `facebook/musicgen-small` (до 30 сек за сегмент, **до 90 сек** со склейкой)
- 🔊 **Звуковые эффекты (Foley)** — `haoheliu/audioldm`
- 🏷️ **Аудиологотипы** — короткие (1-3 сек) звуковые бренды через MusicGen
- 🎚 **Постобработка через FFmpeg**: обрезка, фейды, нормализация (loudnorm),
  конвертация в MP3/OGG, **скачивание файла**, **микширование**, **изменение скорости**
- 🔗 **Автосклейка длинных джинглов** с кроссфейдом между сегментами
- 📚 **Библиотека** сгенерированных звуков с пагинацией, повтором и удалением
- 📊 **Статистика** генераций (`/stats`)
- ⚡ **Очередь и кэш**: не более 2 одновременных запросов к Hugging Face,
  повторные одинаковые запросы отдаются мгновенно из кэша
- 🧠 Опциональное улучшение промтов через Google Gemini (с учётом типа звука)
- 🎧 **3 варианта A/B/C** на каждый запрос + кнопка «Ещё варианты»
- ✨ **Пресеты** (YouTube, Twitch, подкаст…) и **🪄 Мастер** пошагового создания
- 🎚 **Авто-полировка** (normalize + фейды) после каждой генерации
- 👍/👎 **Оценка результата** для улучшения качества
- 🛡 **Middleware**: автoregистрация, антиспам, error handler
- 🔴 **Redis** (опционально) для FSM и сессий · **Sentry** для мониторинга

> Все улучшения бесплатные: без платных API, подписок и монетизации.  
> Gemini опционален; без него работает локальное обогащение промтов.

## Структура проекта

```
jingle_lab_bot/
├── bot.py                     # точка входа (webhook или polling)
├── config.py                  # Pydantic Settings из .env
├── database.py                # SQLite (users, sounds, cache)
├── models/
│   └── enums.py               # GenerationKind
├── states/
│   └── generation.py          # FSM для выбора режима кнопкой
├── texts/
│   └── messages.py            # все пользовательские тексты
├── middlewares/
│   ├── user.py                # авто-регистрация в БД
│   ├── throttling.py          # антиспам
│   └── errors.py              # перехват ошибок
├── handlers/
│   ├── start.py               # /start, /help
│   ├── generate.py            # /jingle, /sound, /logo + свободный текст
│   ├── postprocess.py         # /trim, /fade, /normalize, /format
│   ├── library.py             # /library с пагинацией
│   └── settings.py            # /reset, /stats
├── services/
│   ├── generation_service.py  # оркестрация пайплайна генерации
│   ├── music_stitcher.py      # планирование сегментов длинных джинглов
│   ├── huggingface_service.py # клиент MusicGen/AudioLDM
│   ├── gemini_service.py      # улучшение промтов (опционально)
│   └── ffmpeg_service.py      # постобработка аудио
└── utils/
    ├── queue_service.py       # очередь генерации
    ├── cache.py               # сессия «последний файл»
    ├── callbacks.py           # типизированные callback_data
    ├── filters.py             # кастомные фильтры aiogram
    ├── prompt_parser.py       # разбор длительности и типа звука
    ├── http_client.py         # общий aiohttp session
    ├── keyboards.py           # клавиатуры
    └── helpers.py             # хэши, временные файлы
├── tests/                     # pytest-тесты
├── Dockerfile
└── docker-compose.yml
```

## Docker

```bash
cp .env.example .env
# заполните TELEGRAM_BOT_TOKEN и HF_API_KEY

docker compose up --build -d
```

- База SQLite сохраняется в volume `jinglelab_data`
- `ENABLE_HEALTH_SERVER=1` поднимает `GET /` даже в режиме polling
- Для продакшна задайте `WEBHOOK_HOST` с публичным HTTPS-доменом

## Тесты

```bash
pip install -r requirements-dev.txt
pytest
```

Покрыты: разбор промтов, планирование сегментов, SQLite, кэш сессии, генерация (с моками HF).

## Локальный запуск

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# заполните TELEGRAM_BOT_TOKEN и HF_API_KEY в .env

python bot.py
```

Убедитесь, что в системе установлен `ffmpeg` (`ffmpeg -version`).
Если `WEBHOOK_HOST` не задан — бот автоматически стартует в режиме
long polling, вебхук не требуется.

## Деплой на Railway

1. Создайте новый проект на Railway, подключите этот репозиторий.
2. Railway распознает `nixpacks.toml` и установит `ffmpeg` и Python 3.11.
3. В разделе **Variables** задайте:
   - `TELEGRAM_BOT_TOKEN` — токен от [@BotFather](https://t.me/BotFather)
   - `HF_API_KEY` — токен с [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
   - `GEMINI_API_KEY` — (опционально) ключ Google AI Studio
   - `WEBHOOK_HOST` — публичный домен вашего сервиса Railway
4. Railway автоматически подставит `PORT`.
5. Подключите **Volume** с mount path `/data` — там лежит SQLite (`DB_PATH=/data/jinglelab.db`).
6. Health-check: `GET /` возвращает JSON со статусом и размером очереди.

## Команды бота

| Команда | Описание |
|---------|----------|
| `/jingle [описание]` | Музыкальная заставка |
| `/sound [описание]` | Звуковой эффект |
| `/logo [описание]` | Аудиологотип |
| `/library` | Библиотека звуков |
| `/stats` | Статистика генераций |
| `/trim 0 5` | Обрезка аудио |
| `/fade 0.5 1.0` | Фейды |
| `/normalize` | Нормализация громкости |
| `/format mp3` | Конвертация в MP3 |
| `/download` | Скачать как документ |
| `/mix` | Смикшировать с предыдущим результатом |
| `/speed 1.25` | Изменить скорость (0.5–2.0) |
| `/reset` | Сброс активного файла |

## Дисклеймер

> JINGLE LAB AI генерирует музыку и звуки на основе открытых моделей. Вы
> получаете неограниченное право использовать их в своих проектах, но
> помните, что уникальность не гарантируется, и бот не несёт
> ответственности за совпадения с существующими произведениями.
