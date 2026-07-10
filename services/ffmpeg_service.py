"""
services/ffmpeg_service.py — Обёртка над локальным FFmpeg для постобработки
сгенерированного аудио: обрезка, фейды, нормализация, конвертация формата,
микширование нескольких дорожек.

Все вызовы идут через asyncio.create_subprocess_exec, чтобы не блокировать
event loop. FFmpeg должен быть установлен в системе (см. nixpacks.toml /
apt-пакет ffmpeg на Railway).
"""

import asyncio
import logging
import os

from utils.helpers import new_tmp_path

logger = logging.getLogger("jinglelab.ffmpeg")


class FFmpegError(Exception):
    """Ошибка выполнения команды FFmpeg."""


async def _run_ffmpeg(args: list[str]) -> None:
    """
    Запускает ffmpeg с заданными аргументами и ждёт завершения.
    Бросает FFmpegError с текстом stderr при ненулевом коде возврата.
    """
    cmd = ["ffmpeg", "-y", "-loglevel", "error", *args]
    logger.info("FFmpeg: %s", " ".join(cmd))

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await process.communicate()

    if process.returncode != 0:
        error_text = stderr.decode(errors="ignore")
        logger.error("FFmpeg завершился с ошибкой: %s", error_text[:500])
        raise FFmpegError(f"Ошибка FFmpeg: {error_text[:300]}")


async def trim(input_path: str, start: float, end: float) -> str:
    """Обрезает аудио до диапазона [start, end] секунд."""
    output_path = new_tmp_path(suffix=os.path.splitext(input_path)[1])
    duration = max(end - start, 0.1)
    await _run_ffmpeg(
        ["-i", input_path, "-ss", str(start), "-t", str(duration), output_path]
    )
    return output_path


async def fade(input_path: str, fade_in: float, fade_out: float, total_duration: float) -> str:
    """
    Применяет фейд-ин и фейд-аут.
    total_duration нужен, чтобы правильно рассчитать точку начала fade-out.
    """
    output_path = new_tmp_path(suffix=os.path.splitext(input_path)[1])
    fade_out_start = max(total_duration - fade_out, 0)
    audio_filter = f"afade=t=in:st=0:d={fade_in},afade=t=out:st={fade_out_start}:d={fade_out}"
    await _run_ffmpeg(["-i", input_path, "-af", audio_filter, output_path])
    return output_path


async def normalize(input_path: str) -> str:
    """Нормализует громкость по стандарту EBU R128 (loudnorm)."""
    output_path = new_tmp_path(suffix=os.path.splitext(input_path)[1])
    await _run_ffmpeg(
        ["-i", input_path, "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", output_path]
    )
    return output_path


async def convert_format(input_path: str, target_format: str) -> str:
    """
    Конвертирует аудио в MP3 (320 кбит/с) или OGG (для голосовых сообщений).
    target_format: 'mp3' | 'ogg'
    """
    target_format = target_format.lower().strip(".")
    if target_format not in {"mp3", "ogg"}:
        raise FFmpegError(f"Неподдерживаемый формат: {target_format}")

    output_path = new_tmp_path(suffix=f".{target_format}")

    if target_format == "mp3":
        args = ["-i", input_path, "-codec:a", "libmp3lame", "-b:a", "320k", output_path]
    else:  # ogg — для отправки как голосовое сообщение (opus)
        args = [
            "-i", input_path,
            "-codec:a", "libopus",
            "-b:a", "64k",
            "-vbr", "on",
            output_path,
        ]

    await _run_ffmpeg(args)
    return output_path


async def mix(input_paths: list[str]) -> str:
    """
    Микширует несколько аудиофайлов в один трек (накладывает друг на друга,
    а не склеивает последовательно). Полезно для наложения джингла на
    звуковой эффект.
    """
    if len(input_paths) < 2:
        raise FFmpegError("Для микширования нужно минимум 2 файла.")

    output_path = new_tmp_path(suffix=".wav")
    args: list[str] = []
    for path in input_paths:
        args.extend(["-i", path])

    n = len(input_paths)
    filter_complex = f"amix=inputs={n}:duration=longest:dropout_transition=2"
    args.extend(["-filter_complex", filter_complex, output_path])

    await _run_ffmpeg(args)
    return output_path


async def concat(input_paths: list[str]) -> str:
    """
    Последовательно склеивает несколько аудиофайлов (используется, например,
    когда музыкальный запрос длиннее максимума одной генерации MusicGen).
    """
    if len(input_paths) < 2:
        raise FFmpegError("Для склейки нужно минимум 2 файла.")

    # Формируем временный список файлов для ffmpeg concat demuxer
    list_path = new_tmp_path(suffix=".txt")
    with open(list_path, "w", encoding="utf-8") as f:
        for path in input_paths:
            f.write(f"file '{path}'\n")

    output_path = new_tmp_path(suffix=".wav")
    try:
        await _run_ffmpeg(
            ["-f", "concat", "-safe", "0", "-i", list_path, "-c", "copy", output_path]
        )
    finally:
        os.remove(list_path)

    return output_path


async def concat_with_crossfade(
    input_paths: list[str], crossfade_seconds: float = 0.5
) -> str:
    """
    Склеивает аудиофайлы с плавным кроссфейдом между сегментами.
    """
    if not input_paths:
        raise FFmpegError("Нет файлов для склейки.")
    if len(input_paths) == 1:
        output_path = new_tmp_path(suffix=".wav")
        await _run_ffmpeg(["-i", input_paths[0], output_path])
        return output_path

    output_path = new_tmp_path(suffix=".wav")
    args: list[str] = []
    for path in input_paths:
        args.extend(["-i", path])

    d = max(crossfade_seconds, 0.1)
    if len(input_paths) == 2:
        filter_complex = f"[0:a][1:a]acrossfade=d={d}:c1=tri:c2=tri[aout]"
    else:
        parts = [f"[0:a][1:a]acrossfade=d={d}:c1=tri:c2=tri[a01]"]
        for i in range(2, len(input_paths)):
            prev = f"a{i-1:02d}" if i > 2 else "a01"
            out = f"a{i:02d}" if i < len(input_paths) - 1 else "aout"
            parts.append(
                f"[{prev}][{i}:a]acrossfade=d={d}:c1=tri:c2=tri[{out}]"
            )
        filter_complex = ";".join(parts)

    args.extend(["-filter_complex", filter_complex, "-map", "[aout]", output_path])
    await _run_ffmpeg(args)
    return output_path


async def light_compress(input_path: str) -> str:
    """Лёгкая компрессия для более «студийного» звучания (бесплатно, локально)."""
    output_path = new_tmp_path(suffix=os.path.splitext(input_path)[1])
    await _run_ffmpeg(
        [
            "-i", input_path,
            "-af", "acompressor=threshold=-18dB:ratio=3:attack=5:release=50",
            output_path,
        ]
    )
    return output_path


async def change_speed(input_path: str, speed: float) -> str:
    """Меняет скорость воспроизведения (0.5–2.0) через atempo."""
    speed = max(0.5, min(speed, 2.0))
    output_path = new_tmp_path(suffix=os.path.splitext(input_path)[1])
    await _run_ffmpeg(
        ["-i", input_path, "-af", f"atempo={speed}", output_path]
    )
    return output_path


async def get_duration(input_path: str) -> float:
    """Возвращает длительность аудиофайла в секундах через ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        input_path,
    ]
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        raise FFmpegError(f"ffprobe ошибка: {stderr.decode(errors='ignore')[:300]}")
    try:
        return float(stdout.decode().strip())
    except ValueError:
        return 0.0
