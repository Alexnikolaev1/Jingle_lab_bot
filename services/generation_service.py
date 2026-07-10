"""
services/generation_service.py — Оркестрация пайплайна генерации.
"""

import logging
import os
from collections.abc import Awaitable, Callable

from aiogram import Bot
from aiogram.types import BufferedInputFile, Message

import database as db
from config import DISCLAIMER_TEXT, settings
from models.enums import GenerationKind
from services import audio_polish, ffmpeg_service, gemini_service, huggingface_service
from services.huggingface_service import GenerationResult, HuggingFaceError
from services.music_stitcher import plan_music_segments, segment_prompt
from texts import messages
from utils.cache import LastGeneration, session_cache
from utils.helpers import hash_prompt, new_tmp_path, truncate_text
from utils.keyboards import result_keyboard, variant_pick_keyboard
from utils.prompt_parser import duration_for_kind
from utils.telegram_files import download_telegram_file
from utils.variant_store import AudioVariant, create_batch

logger = logging.getLogger("jinglelab.generation")

ProgressCallback = Callable[[str], Awaitable[None]]


class GenerationService:
    def effective_variant_count(self, remaining_quota: int) -> int:
        desired = min(settings.GENERATION_VARIANTS, 3)
        if settings.DAILY_GENERATION_LIMIT <= 0:
            return desired
        return max(1, min(desired, remaining_quota))

    def _use_variants(
        self, kind: GenerationKind, duration: float, variant_count: int
    ) -> bool:
        if variant_count <= 1:
            return False
        if kind != GenerationKind.MUSIC and kind != GenerationKind.SOUND:
            return False
        if kind == GenerationKind.MUSIC and duration > settings.MAX_MUSIC_DURATION_SECONDS:
            return False
        return True

    async def generate(
        self,
        prompt: str,
        kind: GenerationKind,
        on_progress: ProgressCallback | None = None,
        variant_prompt: str | None = None,
    ) -> tuple[GenerationResult, float, str]:
        """Returns (result, duration, improved_prompt)."""
        improved = variant_prompt or await gemini_service.improve_prompt(prompt, kind)

        if kind == GenerationKind.MUSIC:
            duration = duration_for_kind(prompt, kind)
            if duration <= settings.MAX_MUSIC_DURATION_SECONDS:
                result = await huggingface_service.generate_music(improved, duration)
                return result, duration, improved
            stitched, dur = await self._generate_stitched_music(
                improved, duration, on_progress
            )
            return stitched, dur, improved

        if kind == GenerationKind.SOUND:
            result = await huggingface_service.generate_sound(improved)
            return result, result.duration, improved

        duration = duration_for_kind(prompt, kind)
        result = await huggingface_service.generate_logo(improved, duration)
        return result, duration, improved

    async def _generate_stitched_music(
        self,
        improved_prompt: str,
        total_duration: float,
        on_progress: ProgressCallback | None,
    ) -> tuple[GenerationResult, float]:
        segments = plan_music_segments(total_duration)
        segment_paths: list[str] = []
        total = len(segments)

        for index, seg_duration in enumerate(segments):
            if on_progress:
                await on_progress(
                    messages.GENERATING_SEGMENT.format(
                        current=index + 1, total=total, duration=seg_duration
                    )
                )
            seg_prompt = segment_prompt(improved_prompt, index, total)
            result = await huggingface_service.generate_music(seg_prompt, seg_duration)
            path = new_tmp_path(suffix=".wav")
            with open(path, "wb") as f:
                f.write(result.audio_bytes)
            segment_paths.append(path)

        if on_progress:
            await on_progress(messages.STITCHING_SEGMENTS.format(total=total))

        if len(segment_paths) == 1:
            with open(segment_paths[0], "rb") as f:
                audio_bytes = f.read()
        else:
            final_path = await ffmpeg_service.concat_with_crossfade(
                segment_paths, settings.MUSIC_SEGMENT_CROSSFADE_SECONDS
            )
            with open(final_path, "rb") as f:
                audio_bytes = f.read()

        model_used = (
            "musicgen-small-stitched" if len(segments) > 1 else "musicgen-small"
        )
        return (
            GenerationResult(
                audio_bytes=audio_bytes, model_used=model_used, duration=total_duration
            ),
            total_duration,
        )

    async def _bytes_to_polished_path(
        self, audio_bytes: bytes, duration: float
    ) -> str:
        tmp_path = new_tmp_path(suffix=".wav")
        with open(tmp_path, "wb") as f:
            f.write(audio_bytes)
        return await audio_polish.master_polish(tmp_path, duration)

    async def generate_with_variants(
        self,
        message: Message,
        prompt: str,
        kind: GenerationKind,
        on_progress: ProgressCallback | None = None,
        variant_count: int | None = None,
        generation_prompt: str | None = None,
    ) -> bool:
        """Генерирует A/B/C и предлагает выбрать. True если запущены варианты."""
        duration = duration_for_kind(prompt, kind)
        count = variant_count or min(settings.GENERATION_VARIANTS, 3)
        if not self._use_variants(kind, duration, count):
            return False
        enrichment_base = generation_prompt or prompt
        variant_prompts = await gemini_service.build_variant_prompts(
            enrichment_base, kind, count
        )
        labels = ["A", "B", "C"][:count]
        variants: list[AudioVariant] = []

        for idx, (label, v_prompt) in enumerate(zip(labels, variant_prompts)):
            if on_progress:
                await on_progress(
                    messages.GENERATING_VARIANT.format(
                        label=label, current=idx + 1, total=count
                    )
                )
            result, var_duration, improved = await self.generate(
                prompt, kind, variant_prompt=v_prompt
            )
            path = await self._bytes_to_polished_path(result.audio_bytes, var_duration)
            variants.append(
                AudioVariant(
                    label=label,
                    file_path=path,
                    prompt=prompt,
                    kind=kind.value,
                    duration=var_duration,
                    model_used=result.model_used,
                    improved_prompt=improved,
                )
            )

        batch = await create_batch(message.from_user.id, prompt, kind.value, variants)
        await session_cache.set_last_request(message.from_user.id, prompt, kind.value)

        display_prompt = await gemini_service.translate_for_display(variant_prompts[0])
        await message.answer(
            messages.VARIANTS_READY.format(
                count=count, prompt=truncate_text(display_prompt, 200)
            ),
            reply_markup=variant_pick_keyboard(batch.batch_id, labels),
        )

        for variant in variants:
            with open(variant.file_path, "rb") as f:
                data = f.read()
            await message.answer_audio(
                audio=BufferedInputFile(data, filename=f"variant_{variant.label}.wav"),
                caption=f"🎧 Вариант <b>{variant.label}</b> · {variant.duration:.1f} сек",
            )
        return True

    async def finalize_delivery(
        self,
        message: Message,
        prompt: str,
        kind: GenerationKind,
        file_path: str,
        duration: float,
        model_used: str,
        improved_prompt: str = "",
    ) -> int:
        """Отправляет финальный результат, сохраняет в БД и сессию."""
        user_id = message.from_user.id

        with open(file_path, "rb") as f:
            audio_bytes = f.read()

        stitched_note = ""
        if model_used == "musicgen-small-stitched":
            stitched_note = (
                f"\n🔗 Склеено из {len(plan_music_segments(duration))} сегментов"
            )

        improved_block = ""
        if settings.SHOW_IMPROVED_PROMPT and improved_prompt and improved_prompt != prompt:
            display = await gemini_service.translate_for_display(improved_prompt)
            improved_block = f"\n🧠 Промт AI: <i>{truncate_text(display, 180)}</i>"

        caption = (
            f"{kind.emoji} {kind.label} готов!{stitched_note}\n"
            f"📝 Запрос: {truncate_text(prompt, 200)}\n"
            f"⏱ Длительность: {duration:.1f} сек"
            f"{improved_block}\n\n"
            f"{DISCLAIMER_TEXT}"
        )

        sent = await message.answer_audio(
            audio=BufferedInputFile(audio_bytes, filename=f"{kind.value}.wav"),
            caption=truncate_text(caption, 1024),
            reply_markup=result_keyboard(0),
        )
        file_id = sent.audio.file_id if sent.audio else None

        sound_id = await db.save_sound(
            user_id=user_id,
            prompt=prompt,
            file_id=file_id or "",
            duration=duration,
            model_used=model_used,
            kind=kind.value,
        )

        if sent and sound_id:
            try:
                await sent.edit_reply_markup(reply_markup=result_keyboard(sound_id))
            except Exception:
                pass

        if file_id:
            prompt_hash = hash_prompt(prompt, kind.value, duration)
            await db.cache_set(prompt_hash, file_id)

        await session_cache.set_last(
            user_id,
            LastGeneration(
                file_path=file_path,
                prompt=prompt,
                model_used=model_used,
                duration=duration,
                kind=kind.value,
                sound_id=sound_id,
                improved_prompt=improved_prompt,
            ),
        )
        await session_cache.set_last_request(user_id, prompt, kind.value)

        from utils.tips import random_tip
        await message.answer(random_tip())

        return sound_id

    async def deliver_single(
        self,
        message: Message,
        prompt: str,
        kind: GenerationKind,
        result: GenerationResult,
        duration: float,
        improved_prompt: str,
    ) -> None:
        path = await self._bytes_to_polished_path(result.audio_bytes, duration)
        await self.finalize_delivery(
            message, prompt, kind, path, duration, result.model_used, improved_prompt
        )

    async def try_cached(
        self, message: Message, bot: Bot, prompt: str, kind: GenerationKind
    ) -> bool:
        duration = duration_for_kind(prompt, kind)
        prompt_hash = hash_prompt(prompt, kind.value, duration)
        cached_file_id = await db.cache_get(prompt_hash)
        if not cached_file_id:
            return False

        await message.answer(messages.CACHE_HIT)
        try:
            tmp_path = await download_telegram_file(bot, cached_file_id)
            polished = await audio_polish.master_polish(tmp_path, duration)

            with open(polished, "rb") as f:
                data = f.read()
            sent = await message.answer_audio(
                audio=BufferedInputFile(data, filename=f"{kind.value}.wav"),
                caption=truncate_text(f"📝 {prompt}\n\n{DISCLAIMER_TEXT}", 1024),
                reply_markup=result_keyboard(0),
            )
            file_id = sent.audio.file_id if sent.audio else cached_file_id

            sound_id = await db.save_sound(
                user_id=message.from_user.id,
                prompt=prompt,
                file_id=file_id or "",
                duration=duration,
                model_used="cache",
                kind=kind.value,
            )
            await session_cache.set_last(
                message.from_user.id,
                LastGeneration(
                    file_path=polished,
                    prompt=prompt,
                    model_used="cache",
                    duration=duration,
                    kind=kind.value,
                    sound_id=sound_id,
                ),
            )
            await session_cache.set_last_request(
                message.from_user.id, prompt, kind.value
            )
            if sent and sound_id:
                try:
                    await sent.edit_reply_markup(
                        reply_markup=result_keyboard(sound_id)
                    )
                except Exception:
                    pass
            if file_id and file_id != cached_file_id:
                await db.cache_set(prompt_hash, file_id)
            return True
        except Exception:
            logger.info("Кэшированный file_id недействителен, генерируем заново")
            return False


generation_service = GenerationService()

ModelLoadingError = huggingface_service.ModelLoadingError
RateLimitError = huggingface_service.RateLimitError
CreditsExhaustedError = huggingface_service.CreditsExhaustedError
FalBillingError = huggingface_service.FalBillingError
