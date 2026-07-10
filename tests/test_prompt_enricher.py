from models.enums import GenerationKind
from utils.prompt_enricher import build_local_variants, enrich_prompt


def test_enrich_adds_suffix():
    result = enrich_prompt("джингл", GenerationKind.MUSIC)
    assert "professional jingle" in result.lower() or "studio" in result.lower()


def test_enrich_russian_keywords():
    result = enrich_prompt("спокойное lo-fi intro", GenerationKind.MUSIC)
    assert "lo-fi" in result.lower() or "calm" in result.lower()


def test_local_variants_count():
    variants = build_local_variants("base prompt", 3)
    assert len(variants) == 3
    assert variants[0] != variants[1]
