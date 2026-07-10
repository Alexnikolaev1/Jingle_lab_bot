from enum import StrEnum


class GenerationKind(StrEnum):
    MUSIC = "music"
    SOUND = "sound"
    LOGO = "logo"

    @property
    def emoji(self) -> str:
        return _EMOJI[self]

    @property
    def label(self) -> str:
        return _LABELS[self]


_EMOJI = {
    GenerationKind.MUSIC: "🎼",
    GenerationKind.SOUND: "🔊",
    GenerationKind.LOGO: "🏷️",
}

_LABELS = {
    GenerationKind.MUSIC: "Джингл",
    GenerationKind.SOUND: "Звуковой эффект",
    GenerationKind.LOGO: "Аудиологотип",
}
