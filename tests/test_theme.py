from ios_logger import theme


def test_default_is_light_when_nothing_saved(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert theme.load_mode("X") == theme.LIGHT


def test_saved_mode_survives_reload(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    theme.save_mode("X", theme.DARK)
    assert theme.load_mode("X") == theme.DARK


def test_corrupt_or_unknown_value_falls_back_to_light(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    path = theme.settings_path("X")
    path.parent.mkdir(parents=True)
    path.write_text("{not json", encoding="utf-8")
    assert theme.load_mode("X") == theme.LIGHT
    path.write_text('{"mode": "neon"}', encoding="utf-8")
    assert theme.load_mode("X") == theme.LIGHT


def test_non_string_mode_falls_back_to_light(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    path = theme.settings_path("X")
    path.parent.mkdir(parents=True)
    path.write_text('{"mode": []}', encoding="utf-8")
    assert theme.load_mode("X") == theme.LIGHT


def test_settings_live_under_qa_hub_folder(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert theme.settings_path("Tool") == tmp_path / "QA_Hub" / "Tool" / "theme.json"
