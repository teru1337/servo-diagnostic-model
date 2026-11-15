"""Compatibility and failure tests for persisted normal profiles."""

from pathlib import Path

import pytest

from servo_diagnostic_model.model.statistical_profile import load_profile, save_profile


def test_failed_profile_write_preserves_previous_profile(tmp_path, monkeypatch):
    path = tmp_path / "profile.json"
    save_profile({"version": 1}, str(path))
    write_text = Path.write_text

    def interrupt_after_partial_write(target, data, **kwargs):
        write_text(target, data[:2], **kwargs)
        raise OSError("simulated interrupted write")

    with monkeypatch.context() as patch:
        patch.setattr(Path, "write_text", interrupt_after_partial_write)
        with pytest.raises(OSError, match="simulated interrupted write"):
            save_profile({"version": 2}, str(path))

    assert load_profile(str(path)) == {"version": 1}
    assert list(tmp_path.iterdir()) == [path]
