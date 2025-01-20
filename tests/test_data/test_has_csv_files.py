import pytest
from bmoney.utils.data import has_csv_files


def test_has_csv_files_with_csv_files(tmp_path):
    # Create some CSV files in the temporary directory
    csv_file = tmp_path / "test1.csv"
    csv_file.touch()
    another_csv_file = tmp_path / "test2.csv"
    another_csv_file.touch()

    assert has_csv_files(tmp_path) is True


def test_has_csv_files_without_csv_files(tmp_path):
    # Create some non-CSV files in the temporary directory
    txt_file = tmp_path / "test1.txt"
    txt_file.touch()
    another_file = tmp_path / "test2.docx"
    another_file.touch()

    assert has_csv_files(tmp_path) is False


def test_has_csv_files_with_empty_directory(tmp_path):
    # Test an empty directory
    assert has_csv_files(tmp_path) is False


def test_has_csv_files_invalid_path():
    # Test with an invalid path
    with pytest.raises(Exception, match="Path '.+' is not a directory."):
        has_csv_files("non_existent_path")
