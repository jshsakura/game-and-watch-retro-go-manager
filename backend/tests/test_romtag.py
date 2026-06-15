"""Region tag extraction / filename cleaning."""
from app.services import romtag


# --- region tags are extracted and stripped ---------------------------------

def test_single_region_japan():
    region, cleaned = romtag.extract_region("Antarctic Adventure (Japan).rom")
    assert region == "Japan"
    assert cleaned == "Antarctic Adventure.rom"


def test_multi_region_comma_list():
    region, cleaned = romtag.extract_region("Sonic (USA, Europe, Brazil).md")
    assert region == "USA, Europe, Brazil"
    assert cleaned == "Sonic.md"


def test_korea_region():
    region, cleaned = romtag.extract_region("Game Mo-eumjip 188 Hap (Korea).sms")
    assert region == "Korea"
    assert cleaned == "Game Mo-eumjip 188 Hap.sms"


def test_world():
    region, cleaned = romtag.extract_region("Double Dragon (World).sms")
    assert region == "World"
    assert cleaned == "Double Dragon.sms"


# --- non-region parens are PRESERVED ----------------------------------------

def test_english_title_paren_kept():
    region, cleaned = romtag.extract_region("볼 (Ball).mgw")
    assert region is None
    assert cleaned == "볼 (Ball).mgw"


def test_publisher_tag_kept():
    region, cleaned = romtag.extract_region("Baseball (VTech, Time & Fun).mgw")
    assert region is None
    assert cleaned == "Baseball (VTech, Time & Fun).mgw"


def test_year_tag_kept():
    region, cleaned = romtag.extract_region("Donkey Kong (1982).rom")
    assert region is None
    assert cleaned == "Donkey Kong (1982).rom"


def test_dump_flag_kept():
    # (Unl) is a dump flag, not a region → left in place (region-only scope)
    region, cleaned = romtag.extract_region("Galaxian (Korea) (Unl).sms")
    assert region == "Korea"
    assert cleaned == "Galaxian (Unl).sms"


# --- combined with a preserved title paren ----------------------------------

def test_region_stripped_but_title_paren_kept():
    region, cleaned = romtag.extract_region("록맨 (Rockman) (Japan).nes")
    assert region == "Japan"
    assert cleaned == "록맨 (Rockman).nes"


def test_no_paren_at_all():
    region, cleaned = romtag.extract_region("Alpha Roid.rom")
    assert region is None
    assert cleaned == "Alpha Roid.rom"


# --- region_of across variants ----------------------------------------------

def test_region_of_falls_back_to_second_name():
    # stored_name (Korean, region stripped) lost it; original_name still has it
    region = romtag.region_of("남극탐험.rom", "Antarctic Adventure (Japan).rom")
    assert region == "Japan"


def test_region_of_none_when_absent():
    assert romtag.region_of("Alpha Roid.rom", "알파 로이드.rom") is None
