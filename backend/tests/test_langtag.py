"""Filename → language/Korean-patch detection."""
from app.services import langtag


# --- patch markers (the 꿀렁 J-K convention) ---------------------------------

def test_japanese_to_korean_patch_marker():
    info = langtag.detect("Contra (Korea-patch J-K v20200912 v1.0).nes")
    assert info.orig_lang == "ja"
    assert info.play_lang == "ko"
    assert info.is_korean_patched is True
    assert info.source == "auto"


def test_us_to_korean_patch_marker():
    info = langtag.detect("Some Game (Korea-patch U-K).nes")
    assert info.orig_lang == "en"
    assert info.play_lang == "ko"
    assert info.is_korean_patched is True


def test_unlicensed_to_korean_patch_marker():
    info = langtag.detect("Pirate (Korea-patch Unl-K).nes")
    assert info.orig_lang == "unl"
    assert info.is_korean_patched is True


def test_patch_marker_with_trailing_date():
    info = langtag.detect("Crisis Force (Korea-patch J-K 20080823).nes")
    assert info.is_korean_patched is True
    assert info.orig_lang == "ja"


# --- region tags (no patch → play == original) ------------------------------

def test_region_japan_no_patch():
    info = langtag.detect("Super Mario Bros. (Japan).nes")
    assert info.orig_lang == "ja"
    assert info.play_lang == "ja"
    assert info.is_korean_patched is False


def test_region_usa_no_patch():
    info = langtag.detect("Sonic (USA).md")
    assert info.orig_lang == "en"
    assert info.is_korean_patched is False


def test_unknown_name_is_all_none():
    info = langtag.detect("볼 (Ball).gw")
    assert info.orig_lang is None
    assert info.play_lang is None
    assert info.is_korean_patched is False


def test_empty_filename_does_not_raise():
    info = langtag.detect("")
    assert info.is_korean_patched is False


# --- detect_any (backfill from original + stored names) ---------------------

def test_detect_any_prefers_patch_signal_from_original_name():
    # stored_name is already Korean (marker lost), original_name still has it
    info = langtag.detect_any("콘트라.nes", "Contra (Korea-patch J-K v1.0).nes")
    assert info.is_korean_patched is True
    assert info.orig_lang == "ja"


def test_detect_any_falls_back_to_region_when_no_patch():
    info = langtag.detect_any("소닉.md", "Sonic (USA).md")
    assert info.is_korean_patched is False
    assert info.orig_lang == "en"


def test_detect_any_all_unknown():
    info = langtag.detect_any("볼.gw", "볼 (Ball).gw")
    assert info.orig_lang is None
    assert info.is_korean_patched is False


# --- manual override --------------------------------------------------------

def test_manual_patch_overrides_and_marks_source():
    base = langtag.detect("Super Mario Bros. (Japan).nes")  # ja / not patched
    forced = langtag.manual_patch(base, True)
    assert forced.is_korean_patched is True
    assert forced.play_lang == "ko"
    assert forced.source == "manual"
    # original info is unchanged (immutability)
    assert base.is_korean_patched is False
    assert base.source == "auto"


def test_manual_unpatch_reverts_play_lang_to_original():
    base = langtag.detect("Contra (Korea-patch J-K).nes")   # ja → ko
    forced = langtag.manual_patch(base, False)
    assert forced.is_korean_patched is False
    assert forced.play_lang == "ja"
    assert forced.source == "manual"
