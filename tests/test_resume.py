import pytest

from app.services.resume import extract_resume_text


def test_resume_rejects_other_formats(tmp_path):
    path = tmp_path / "resume.txt"
    path.write_text("Resume")
    with pytest.raises(ValueError):
        extract_resume_text(str(path))
