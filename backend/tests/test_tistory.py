"""Blog search parsing + match logic (pure, no network)."""
from app.services import tistory

# A trimmed search page: the anchors are what parse_results keys on.
HTML = """
<div class="search">
  <a href="/5479"> [GG] 더블 드래곤 / Double Dragon </a>
  <a href="/3463"> [SMS] 더블 드래곤 / Double Dragon </a>
  <a href="/4399"> [NES] 더블 드래곤 3 로제타 스톤 / Double Dragon 3 - The Rosetta Stone </a>
  <a href="/9001"> [GG] 바람돌이 소닉, 소닉 더 헷지혹 / Sonic The Hedgehog </a>
  <a href="/9002"> [GG] 베어 너클 2 / Bare Knuckle II </a>
</div>
"""


def test_parse_extracts_sys_korean_english():
    rows = tistory.parse_results(HTML)
    byurl = {r["url"]: r for r in rows}
    assert byurl["/5479"]["sys"] == "gg"
    assert byurl["/5479"]["korean"] == "더블 드래곤"
    assert "Double Dragon" in byurl["/5479"]["engs"]


def test_exact_match_requires_system_tag():
    rows = tistory.parse_results(HTML)
    # Double Dragon on GG must pick the [GG] post, not [SMS]/[NES]
    m = tistory.best_match("gg", "Double Dragon (USA, Europe).gg", rows)
    assert m["confidence"] == "exact"
    assert m["korean"] == "더블 드래곤"
    assert m["url"] == "/5479"


def test_exact_match_for_sms_is_the_sms_post():
    rows = tistory.parse_results(HTML)
    m = tistory.best_match("sms", "Double Dragon (World).sms", rows)
    assert m["url"] == "/3463"


def test_first_alias_is_used():
    rows = tistory.parse_results(HTML)
    m = tistory.best_match("gg", "Sonic The Hedgehog (USA, Europe).gg", rows)
    # '바람돌이 소닉, 소닉 더 헷지혹' -> first alias only
    assert m["korean"] == "바람돌이 소닉"
    assert m["confidence"] == "exact"


def test_fuzzy_when_english_differs():
    rows = tistory.parse_results(HTML)
    # 'Bare Knuckle' vs blog 'Bare Knuckle II' → system matches, English doesn't
    m = tistory.best_match("gg", "Bare Knuckle (World).gg", rows)
    assert m["confidence"] == "fuzzy"
    assert m["korean"] == "베어 너클 2"


def test_no_match_returns_none():
    rows = tistory.parse_results(HTML)
    assert tistory.best_match("pce", "Some Other Game.pce", rows) is None


def test_clean_query_strips_region_and_ext():
    assert tistory.clean_query("Double Dragon (USA, Europe).gg") == "Double Dragon"
    assert tistory.clean_query("Sonic ~ Bare Knuckle (World).gg") == "Sonic"
