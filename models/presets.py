"""Откалиброванные пресеты — промты вручную настроены под MusicGen/AudioLDM."""

from dataclasses import dataclass

from models.enums import GenerationKind

DEMO_PRESET_ID = "youtube"


@dataclass(frozen=True)
class Preset:
    id: str
    title: str
    emoji: str
    kind: GenerationKind
    prompt: str
    calibrated_prompt: str
    featured: bool = False
    category: str = "general"
    tip: str = ""

    @property
    def generation_prompt(self) -> str:
        return self.calibrated_prompt


PRESETS: tuple[Preset, ...] = (
    Preset(
        id="youtube",
        title="YouTube",
        emoji="▶️",
        kind=GenerationKind.MUSIC,
        category="video",
        featured=True,
        tip="Идеален как интро для видео — после генерации жми «🔁 В MP3».",
        prompt="Энергичный 12-секундный джингл для YouTube-канала",
        calibrated_prompt=(
            "Upbeat modern pop intro jingle for YouTube channel, 120 BPM, "
            "bright synths, punchy drums, catchy hook, clean studio mix, 12 seconds"
        ),
    ),
    Preset(
        id="podcast",
        title="Подкаст",
        emoji="🎙",
        kind=GenerationKind.MUSIC,
        category="video",
        featured=True,
        tip="Lo-fi intro — спокойное начало выпуска без резких пиков.",
        prompt="Спокойное lo-fi intro для подкаста, 8 секунд",
        calibrated_prompt=(
            "Warm lo-fi podcast intro, 85 BPM, mellow Rhodes piano, soft vinyl crackle, "
            "relaxed mood, smooth fade-in, professional broadcast quality, 8 seconds"
        ),
    ),
    Preset(
        id="twitch",
        title="Twitch",
        emoji="🟣",
        kind=GenerationKind.MUSIC,
        category="stream",
        featured=True,
        tip="Короткий alert — вставь в OBS как звук доната или подписчика.",
        prompt="Короткий alert для Twitch-стрима, 5 секунд",
        calibrated_prompt=(
            "Short energetic Twitch stream alert sting, 128 BPM, electronic drop, "
            "glitch accents, bold and punchy, 5 seconds, gaming broadcast style"
        ),
    ),
    Preset(
        id="notification",
        title="Уведомление",
        emoji="🔔",
        kind=GenerationKind.LOGO,
        category="brand",
        featured=True,
        tip="Короткий UI-звук — подойдёт для приложения или бота.",
        prompt="Приятный звук уведомления для приложения, 2 сек",
        calibrated_prompt=(
            "Pleasant mobile app notification sound logo, soft bell tone, "
            "friendly and subtle, modern UI design, 2 seconds sting"
        ),
    ),
    Preset(
        id="cafe",
        title="Кофейня",
        emoji="☕",
        kind=GenerationKind.LOGO,
        category="brand",
        tip="Тёплый бренд-звук для кафе, магазина или блога.",
        prompt="Уютный аудиологотип для кофейни, 2 секунды",
        calibrated_prompt=(
            "Warm cozy coffee shop audio logo, acoustic guitar pluck, gentle shimmer, "
            "inviting brand identity, soft and memorable, 2 seconds"
        ),
    ),
    Preset(
        id="cinematic",
        title="Кино",
        emoji="🎬",
        kind=GenerationKind.MUSIC,
        category="video",
        tip="Длиннее 30 сек — бот сам склеит сегменты. Укажи «20 секунд» в промте.",
        prompt="Эпичное cinematic intro для трейлера, 20 секунд",
        calibrated_prompt=(
            "Epic cinematic trailer intro, 90 BPM building to 110 BPM, "
            "orchestral strings, brass hits, dramatic tension, Hans Zimmer style, "
            "20 seconds, wide soundstage"
        ),
    ),
    Preset(
        id="fitness",
        title="Фитнес",
        emoji="💪",
        kind=GenerationKind.MUSIC,
        category="video",
        tip="Мотивация для спортивного контента — энергично и без лишней мути.",
        prompt="Мотивирующий джингл для фитнес-блога, 8 секунд",
        calibrated_prompt=(
            "Motivational fitness vlog intro, 128 BPM, energetic EDM, "
            "driving four-on-the-floor beat, powerful and uplifting, 8 seconds"
        ),
    ),
    Preset(
        id="tiktok",
        title="TikTok",
        emoji="📱",
        kind=GenerationKind.MUSIC,
        category="video",
        tip="Короткий хук — первые секунды ролика решают всё.",
        prompt="Цепляющий 6-секундный хук для TikTok/Reels",
        calibrated_prompt=(
            "Catchy TikTok hook intro, 130 BPM, trendy pop beat, "
            "instant attention grabber, viral short-form style, 6 seconds"
        ),
    ),
    Preset(
        id="magic",
        title="Магия",
        emoji="✨",
        kind=GenerationKind.SOUND,
        category="sfx",
        tip="Звук для перехода, появления предмета или UI в игре.",
        prompt="Волшебное появление предмета, fantasy UI",
        calibrated_prompt=(
            "Magical item spawn sound effect, sparkling chime, fantasy game UI, "
            "crystalline texture, short bright swell, no music"
        ),
    ),
    Preset(
        id="explosion",
        title="Взрыв",
        emoji="💥",
        kind=GenerationKind.SOUND,
        category="sfx",
        tip="Для монтажа — после генерации можно /mix с музыкой.",
        prompt="Кинематографичный взрыв в большом помещении",
        calibrated_prompt=(
            "Cinematic explosion sound effect, deep boom, debris rumble, "
            "warehouse reverb tail, dramatic impact, film quality foley"
        ),
    ),
    Preset(
        id="rain",
        title="Дождь",
        emoji="🌧",
        kind=GenerationKind.SOUND,
        category="sfx",
        tip="Ambient-фон для медитации, стрима или фона в подкасте.",
        prompt="Атмосферный звук дождя за окном",
        calibrated_prompt=(
            "Cozy rain on window ambient sound, gentle steady rainfall, "
            "indoor perspective, relaxing atmosphere, natural foley, no music"
        ),
    ),
    Preset(
        id="whoosh",
        title="Whoosh",
        emoji="💨",
        kind=GenerationKind.SOUND,
        category="sfx",
        tip="Классика монтажа — переход между сценами.",
        prompt="Cinematic whoosh для перехода между сценами",
        calibrated_prompt=(
            "Cinematic transition whoosh sound effect, fast air sweep, "
            "modern trailer style, clean and punchy, short duration"
        ),
    ),
)

PRESET_BY_ID = {p.id: p for p in PRESETS}
FEATURED_PRESETS = tuple(p for p in PRESETS if p.featured)
CATEGORIES = {
    "video": ("🎬 Видео", ("youtube", "podcast", "cinematic", "fitness", "tiktok")),
    "stream": ("📡 Стрим", ("twitch",)),
    "brand": ("🏷️ Бренд", ("notification", "cafe")),
    "sfx": ("🔊 SFX", ("magic", "explosion", "rain", "whoosh")),
}
