"""Тесты откалиброванных пресетов."""

from models.enums import GenerationKind
from models.presets import (
    CATEGORIES,
    DEMO_PRESET_ID,
    FEATURED_PRESETS,
    PRESET_BY_ID,
    PRESETS,
)


def test_all_presets_have_calibrated_prompts():
    for preset in PRESETS:
        assert preset.calibrated_prompt.strip()
        assert preset.calibrated_prompt != preset.prompt
        assert preset.generation_prompt == preset.calibrated_prompt


def test_demo_preset_is_youtube():
    demo = PRESET_BY_ID[DEMO_PRESET_ID]
    assert demo.title == "YouTube"
    assert demo.kind == GenerationKind.MUSIC


def test_featured_presets_subset():
    assert len(FEATURED_PRESETS) >= 3
    featured_ids = {p.id for p in FEATURED_PRESETS}
    assert all(p.featured for p in FEATURED_PRESETS)
    assert featured_ids.issubset({p.id for p in PRESETS})


def test_categories_cover_all_presets():
    covered = set()
    for _cat_id, (_label, preset_ids) in CATEGORIES.items():
        covered.update(preset_ids)
    assert covered == {p.id for p in PRESETS}
