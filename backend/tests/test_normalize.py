"""Per-rom normalization planning (pure, injected resolver)."""
from app.services import normalize


def _no_resolver(system, stored):
    return None


def _fake_resolver(korean, confidence="exact"):
    return lambda system, stored: {"korean": korean, "confidence": confidence, "url": "/1"}


# --- needs_korean scope -----------------------------------------------------

def test_needs_korean_true_for_english_title():
    assert normalize.needs_korean("Bravoman (USA).pce", "pce") is True


def test_needs_korean_false_for_hangul():
    assert normalize.needs_korean("버블 보블 (Bubble Bobble).gg", "gg") is False


def test_needs_korean_false_for_acronym_and_number():
    assert normalize.needs_korean("1942.nes", "nes") is False
    assert normalize.needs_korean("NBA Jam.md", "md") is True   # has real word 'Jam'
    assert normalize.needs_korean("Z.O.E.gba", "gbc") is False  # only single letters


def test_needs_korean_false_for_excluded_systems():
    assert normalize.needs_korean("Cool Indie Game.p8.png", "pico8") is False
    assert normalize.needs_korean("Some Homebrew.nes", "homebrew") is False


# --- plan_rom: region strip -------------------------------------------------

def test_region_only_strip_when_no_resolver_hit():
    p = normalize.plan_rom("pce", "Bravoman (USA).pce", _no_resolver)
    assert p["region"] == "USA"
    assert p["new_stored"] == "Bravoman.pce"
    assert p["changed"] is True
    assert p["korean"] is None


def test_korean_fill_composes_korean_english():
    p = normalize.plan_rom("gg", "Bubble Bobble (USA).gg", _fake_resolver("버블 보블"))
    assert p["region"] == "USA"
    assert p["new_stored"] == "버블 보블 (Bubble Bobble).gg"
    assert p["korean"] == "버블 보블"
    assert p["confidence"] == "exact"
    assert p["changed"] is True


def test_fuzzy_confidence_passthrough():
    p = normalize.plan_rom("gg", "Bare Knuckle (World).gg", _fake_resolver("베어 너클 2", "fuzzy"))
    assert p["confidence"] == "fuzzy"
    assert p["korean"] == "베어 너클 2"


def test_already_korean_only_strips_region():
    p = normalize.plan_rom("gg", "남극탐험 (Antarctic Adventure).rom", _fake_resolver("X"))
    # has Hangul → resolver not consulted; no region tag → unchanged
    assert p["korean"] is None
    assert p["changed"] is False


def test_excluded_system_no_korean_lookup():
    p = normalize.plan_rom("pico8", "Celeste.p8.png", _fake_resolver("셀레스트"))
    assert p["korean"] is None
