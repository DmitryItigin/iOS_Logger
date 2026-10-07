from ios_logger.logic import extract_level, line_visible

LINE = "12:00:00.000 ERROR   MyApp[42]: Something Failed"


def test_extract_level_reads_second_field():
    assert extract_level(LINE) == "ERROR"


def test_unknown_or_short_line_maps_to_no_level():
    assert extract_level("garbage") == "-"
    assert extract_level("12:00 WEIRD proc[1]: x") == "-"


def test_filter_text_is_case_insensitive_substring():
    assert line_visible(LINE, "something", {"ERROR"})
    assert not line_visible(LINE, "missing", {"ERROR"})


def test_disabled_level_hides_line():
    assert not line_visible(LINE, "", {"INFO"})
