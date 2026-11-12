import io

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
