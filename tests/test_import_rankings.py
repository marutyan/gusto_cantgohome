import pytest

from scripts.import_rankings import validate


def test_validate_requires_contiguous_ranks():
    rows = [
        {"総合順位": 1, "メニュー名": "A", "カテゴリ": "C"},
        {"総合順位": 3, "メニュー名": "B", "カテゴリ": "C"},
    ]
    with pytest.raises(ValueError, match="contiguous"):
        validate(rows, expected_count=2)


def test_validate_accepts_expected_rows():
    rows = [
        {"総合順位": 1, "メニュー名": "A", "カテゴリ": "C"},
        {"総合順位": 2, "メニュー名": "B", "カテゴリ": "C"},
    ]
    assert len(validate(rows, expected_count=2)) == 2
