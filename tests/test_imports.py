from imports import Import


def test_standard_probe_ignores_shadowing_from_cwd(tmp_path, monkeypatch):
    (tmp_path / 'glob.py').write_text("raise RuntimeError('shadowed glob')")
    monkeypatch.chdir(tmp_path)
    Import._check_standard.cache_clear()
    try:
        assert Import('pathlib').standard()
    finally:
        Import._check_standard.cache_clear()
