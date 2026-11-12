import io
import json

import pytest

from endpoint import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    return app.test_client()


def test_clean_non_utf8_file_returns_error_message(client):
    data = {
        "fromfile": "1",
        "bibfile": (io.BytesIO("@article{a, title={テスト}}".encode("shift_jis")), "a.bib"),
    }
    res = client.post("/clean", data=data, content_type="multipart/form-data")
    assert res.status_code == 200
    assert res.mimetype == "text/plain"
    assert res.get_data(as_text=True).startswith("Error.")


def test_clean_empty_title_with_savetitlecase(client):
    bib = "@article{a,\n  author = {Doe, John},\n  title = {},\n  journal = {J},\n  year = {2020},\n}\n"
    res = client.post("/clean", data={"fromtext": "1", "bibtext": bib, "savetitlecase": "on"})
    assert res.status_code == 200
    assert not res.get_data(as_text=True).startswith("Error.")


def test_clean_unexpected_exception_returns_error_message(client, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("unexpected")

    monkeypatch.setattr("endpoint.bibtex_cleaner", boom)
    res = client.post("/clean", data={"fromtext": "1", "bibtext": "@misc{a}"})
    assert res.status_code == 200
    body = res.get_data(as_text=True)
    assert body.startswith("Error.")
    assert "unexpected" not in body


SORT_BIB = "@misc{Zeta2020, title={Z}, year={2020}}\n@misc{Alpha2021, title={A}, year={2021}}\n"


def test_clean_sort_id(client):
    res = client.post("/clean", data={"fromtext": "1", "bibtext": SORT_BIB, "sort": "id"})
    body = res.get_data(as_text=True)
    assert body.index("Alpha2021") < body.index("Zeta2020")


@pytest.mark.parametrize("sort", [None, "input", "bogus"])
def test_clean_sort_defaults_to_input(client, sort):
    data = {"fromtext": "1", "bibtext": SORT_BIB}
    if sort is not None:
        data["sort"] = sort
    body = client.post("/clean", data=data).get_data(as_text=True)
    assert body.index("Zeta2020") < body.index("Alpha2021")


FIELDS_BIB = "@article{a,\n  author = {Doe, John},\n  title = {T},\n  journal = {J},\n  year = {2020},\n  number = {3},\n  doi = {10.1/x},\n}\n"


def test_clean_with_fields(client):
    fields = {"add": {"article": ["doi"]}, "remove": {"article": ["number"]}}
    data = {"fromtext": "1", "bibtext": FIELDS_BIB, "fields": json.dumps(fields)}
    body = client.post("/clean", data=data).get_data(as_text=True)
    assert "doi = {10.1/x}" in body
    assert "number" not in body


@pytest.mark.parametrize("fields", ["", "not json", "[1, 2]", '{"add": {"article": "doi"}}'])
def test_clean_with_invalid_fields_uses_defaults(client, fields):
    data = {"fromtext": "1", "bibtext": FIELDS_BIB, "fields": fields}
    body = client.post("/clean", data=data).get_data(as_text=True)
    assert not body.startswith("Error.")
    assert "doi" not in body
    assert "number = {3}" in body


def test_clean_save_doi_still_supported(client):
    data = {"fromtext": "1", "bibtext": FIELDS_BIB, "save_doi": "on"}
    body = client.post("/clean", data=data).get_data(as_text=True)
    assert "doi = {10.1/x}" in body


def test_index_renders_field_settings(client):
    body = client.get("/").get_data(as_text=True)
    assert 'id="field-settings"' in body
    # エントリタイプはスキーマの定義順で渡す（tojsonのキーソートで順序が崩れないこと）
    assert body.index('["article", [') < body.index('["inproceedings", [') < body.index('["phdthesis", [')
    assert 'name="save_doi"' not in body
