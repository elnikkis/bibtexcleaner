import pytest
from bibtexparser.bibdatabase import BibDatabase

from cleaner import (
    bibtex_cleaner,
    page_double_hyphen,
    split_author,
    remove_line_breaks,
    _is_japanese,
    check_parentheses_matching,
    _wrap_title,
    _make_id,
    _treat_japanese_author,
    clean_entry,
    clean_entries,
    CleanerException,
    sanitize_field_settings,
    parse_field_list,
)
from bibtex_schema import required as required_fields


# ---------------------------------------------------------------------------
# page_double_hyphen
# ---------------------------------------------------------------------------

def test_page_double_hyphen_already_double():
    record = {"pages": "440--442"}
    assert page_double_hyphen(record)["pages"] == "440--442"


def test_page_double_hyphen_single_hyphen():
    record = {"pages": "440-442"}
    assert page_double_hyphen(record)["pages"] == "440--442"


def test_page_double_hyphen_en_dash():
    record = {"pages": "440–442"}
    assert page_double_hyphen(record)["pages"] == "440--442"


def test_page_double_hyphen_em_dash():
    record = {"pages": "440—442"}
    assert page_double_hyphen(record)["pages"] == "440--442"


def test_page_double_hyphen_no_pages_field():
    record = {"title": "Some Title"}
    result = page_double_hyphen(record)
    assert "pages" not in result


def test_page_double_hyphen_with_spaces():
    record = {"pages": "440 - 442"}
    assert page_double_hyphen(record)["pages"] == "440--442"


# ---------------------------------------------------------------------------
# split_author
# ---------------------------------------------------------------------------

def test_split_author_single():
    record = {"author": "Smith, John"}
    result = split_author(record)
    assert result["author"] == ["Smith, John"]


def test_split_author_multiple():
    record = {"author": "Smith, John and Doe, Jane and Brown, Bob"}
    result = split_author(record)
    assert result["author"] == ["Smith, John", "Doe, Jane", "Brown, Bob"]


def test_split_author_no_field():
    record = {"title": "Some Title"}
    result = split_author(record)
    assert "author" not in result


def test_split_author_empty_string():
    record = {"author": ""}
    result = split_author(record)
    # empty string is falsy, so author stays unchanged
    assert result["author"] == ""


# ---------------------------------------------------------------------------
# remove_line_breaks
# ---------------------------------------------------------------------------

def test_remove_line_breaks_author_string():
    record = {"author": "Smith,\nJohn"}
    result = remove_line_breaks(record)
    assert "\n" not in result["author"]
    assert result["author"] == "Smith, John"


def test_remove_line_breaks_title():
    record = {"title": "Some\nTitle"}
    result = remove_line_breaks(record)
    assert result["title"] == "Some Title"


def test_remove_line_breaks_author_list():
    record = {"author": ["Smith,\nJohn", "Doe,\nJane"]}
    result = remove_line_breaks(record)
    assert result["author"] == ["Smith, John", "Doe, Jane"]


def test_remove_line_breaks_ignores_year():
    record = {"year": "19\n98"}
    result = remove_line_breaks(record)
    assert result["year"] == "19\n98"


# ---------------------------------------------------------------------------
# _is_japanese
# ---------------------------------------------------------------------------

def test_is_japanese_hiragana():
    assert _is_japanese("あいう") is True


def test_is_japanese_katakana():
    assert _is_japanese("アイウ") is True


def test_is_japanese_cjk():
    assert _is_japanese("漢字") is True


def test_is_japanese_ascii_only():
    assert _is_japanese("hello") is False


def test_is_japanese_empty():
    assert _is_japanese("") is False


def test_is_japanese_mixed():
    assert _is_japanese("hello世界") is True


# ---------------------------------------------------------------------------
# check_parentheses_matching
# ---------------------------------------------------------------------------

def test_check_parentheses_empty():
    assert check_parentheses_matching("", "{", "}") is True


def test_check_parentheses_matched():
    assert check_parentheses_matching("{abc}", "{", "}") is True


def test_check_parentheses_nested():
    assert check_parentheses_matching("{{abc}}", "{", "}") is True


def test_check_parentheses_missing_close():
    assert check_parentheses_matching("{abc", "{", "}") is False


def test_check_parentheses_missing_open():
    assert check_parentheses_matching("abc}", "{", "}") is False


def test_check_parentheses_two_pairs():
    assert check_parentheses_matching("{abc}{def}", "{", "}") is True


# ---------------------------------------------------------------------------
# _wrap_title
# ---------------------------------------------------------------------------

def test_wrap_title_no_braces():
    entry = {"title": "Some Title"}
    result = _wrap_title(entry)
    assert result["title"] == "{Some Title}"


def test_wrap_title_already_wrapped():
    entry = {"title": "{Some Title}"}
    result = _wrap_title(entry)
    assert result["title"] == "{Some Title}"


def test_wrap_title_internal_braces():
    # "{foo} and {bar}" — outer braces don't match as a single pair
    entry = {"title": "{foo} and {bar}"}
    result = _wrap_title(entry)
    assert result["title"] == "{{foo} and {bar}}"


def test_wrap_title_empty():
    entry = {"title": ""}
    result = _wrap_title(entry)
    assert result["title"] == ""


def test_wrap_title_single_brace():
    entry = {"title": "{"}
    result = _wrap_title(entry)
    assert result["title"] == "{{}"


def test_wrap_title_no_field():
    entry = {"author": "Smith, John"}
    result = _wrap_title(entry)
    assert "title" not in result


# ---------------------------------------------------------------------------
# _make_id
# ---------------------------------------------------------------------------

def test_make_id_normal():
    entry = {"ID": "old", "author": ["Smith, John"], "year": "2010"}
    assert _make_id(entry) == "Smith2010"


def test_make_id_no_author():
    entry = {"ID": "old", "year": "2010"}
    assert _make_id(entry) == "old"


def test_make_id_no_year():
    entry = {"ID": "old", "author": ["Smith, John"]}
    assert _make_id(entry) == "old"


def test_make_id_last_only():
    entry = {"ID": "old", "author": ["Smith"], "year": "2020"}
    # splitname("Smith") puts "Smith" in last
    result = _make_id(entry)
    assert result == "Smith2020"


# ---------------------------------------------------------------------------
# _treat_japanese_author
# ---------------------------------------------------------------------------

def test_treat_japanese_author_normal_order():
    entry = {"author": ["山田, 太郎"]}
    result = _treat_japanese_author(entry, reverse_author=False)
    assert result["author"] == ["山田 太郎"]


def test_treat_japanese_author_reverse():
    entry = {"author": ["山田, 太郎"]}
    result = _treat_japanese_author(entry, reverse_author=True)
    assert result["author"] == ["太郎 山田"]


def test_treat_japanese_author_english_unchanged():
    entry = {"author": ["Smith, John"]}
    result = _treat_japanese_author(entry, reverse_author=False)
    assert result["author"] == ["Smith, John"]


def test_treat_japanese_author_mixed():
    entry = {"author": ["山田, 太郎", "Smith, John"]}
    result = _treat_japanese_author(entry, reverse_author=False)
    assert result["author"] == ["山田 太郎", "Smith, John"]


# ---------------------------------------------------------------------------
# clean_entry
# ---------------------------------------------------------------------------

BASE_OPTION = {
    "savetitlecase": False,
    "replaceid": False,
    "jauthor": False,
    "revjauthor": False,
    "save_doi": False,
}


def test_clean_entry_removes_extra_fields():
    entry = {
        "ID": "Smith2020",
        "ENTRYTYPE": "article",
        "author": ["Smith, John"],
        "title": "A Title",
        "journal": "Nature",
        "year": "2020",
        "volume": "1",
        "number": "2",
        "pages": "1--10",
        "annote": "should be removed",
        "file": "should be removed",
    }
    result = clean_entry(entry, BASE_OPTION)
    assert "annote" not in result
    assert "file" not in result
    assert result["author"] == "Smith, John"


def test_clean_entry_save_doi_true():
    entry = {
        "ID": "Smith2020",
        "ENTRYTYPE": "article",
        "author": ["Smith, John"],
        "title": "A Title",
        "journal": "Nature",
        "year": "2020",
        "volume": "1",
        "number": "2",
        "pages": "1--10",
        "doi": "10.1234/test",
    }
    option = {**BASE_OPTION, "save_doi": True}
    result = clean_entry(entry, option)
    assert result["doi"] == "10.1234/test"


def test_clean_entry_save_doi_false():
    entry = {
        "ID": "Smith2020",
        "ENTRYTYPE": "article",
        "author": ["Smith, John"],
        "title": "A Title",
        "journal": "Nature",
        "year": "2020",
        "volume": "1",
        "number": "2",
        "pages": "1--10",
        "doi": "10.1234/test",
    }
    result = clean_entry(entry, BASE_OPTION)
    assert "doi" not in result


def test_clean_entry_unknown_type_raises():
    entry = {
        "ID": "X2020",
        "ENTRYTYPE": "unknowntype",
        "author": ["Smith, John"],
    }
    with pytest.raises(CleanerException):
        clean_entry(entry, BASE_OPTION)


# ---------------------------------------------------------------------------
# clean_entries — duplicate ID handling
# ---------------------------------------------------------------------------

def _make_db(entries):
    db = BibDatabase()
    db.entries = entries
    return db


def test_clean_entries_duplicate_id_two():
    entries = [
        {
            "ID": "Smith2020",
            "ENTRYTYPE": "inproceedings",
            "author": ["Smith, John"],
            "title": "First Paper",
            "booktitle": "Conf",
            "year": "2020",
            "pages": "1--5",
        },
        {
            "ID": "Smith2020",
            "ENTRYTYPE": "inproceedings",
            "author": ["Smith, John"],
            "title": "Second Paper",
            "booktitle": "Conf",
            "year": "2020",
            "pages": "6--10",
        },
    ]
    db = _make_db(entries)
    result = clean_entries(db, BASE_OPTION)
    ids = [e["ID"] for e in result.entries]
    assert ids == ["Smith2020a", "Smith2020b"]


def test_clean_entries_duplicate_id_three():
    entries = [
        {
            "ID": "X",
            "ENTRYTYPE": "inproceedings",
            "author": ["A, B"],
            "title": "T1",
            "booktitle": "C",
            "year": "2000",
            "pages": "1--2",
        },
        {
            "ID": "X",
            "ENTRYTYPE": "inproceedings",
            "author": ["A, B"],
            "title": "T2",
            "booktitle": "C",
            "year": "2000",
            "pages": "3--4",
        },
        {
            "ID": "X",
            "ENTRYTYPE": "inproceedings",
            "author": ["A, B"],
            "title": "T3",
            "booktitle": "C",
            "year": "2000",
            "pages": "5--6",
        },
    ]
    db = _make_db(entries)
    result = clean_entries(db, BASE_OPTION)
    ids = [e["ID"] for e in result.entries]
    assert ids == ["Xa", "Xb", "Xc"]


# ---------------------------------------------------------------------------
# bibtex_cleaner integration tests
# ---------------------------------------------------------------------------

INPROCEEDINGS_BIB = """
@inproceedings{Doe2021,
  author = {Doe, John},
  title = {A Great Paper},
  booktitle = {Proceedings of Something},
  year = {2021},
  pages = {10-20},
  doi = {10.1234/foo},
  file = {:some/path.pdf:pdf},
}
"""

DEFAULT_OPTION = {
    "savetitlecase": False,
    "replaceid": False,
    "jauthor": False,
    "revjauthor": False,
    "save_doi": False,
}


def test_bibtex_cleaner_inproceedings():
    result = bibtex_cleaner(INPROCEEDINGS_BIB, DEFAULT_OPTION)
    assert "Doe2021" in result
    assert "file" not in result
    assert "doi" not in result
    assert "10--20" in result


def test_bibtex_cleaner_replaceid():
    option = {**DEFAULT_OPTION, "replaceid": True}
    result = bibtex_cleaner(INPROCEEDINGS_BIB, option)
    assert "Doe2021" in result


def test_bibtex_cleaner_unknown_type_silently_ignored():
    # bibtexparser silently drops unknown entry types; no exception is raised
    bib = """
@unknowntype{X2020,
  author = {Smith, John},
  title = {A Title},
  year = {2020},
}
"""
    result = bibtex_cleaner(bib, DEFAULT_OPTION)
    assert "X2020" not in result


def test_bibtex_cleaner_multiple_entries():
    bib = """
@inproceedings{A2021,
  author = {Alpha, A},
  title = {Title A},
  booktitle = {Conf},
  year = {2021},
  pages = {1--5},
}
@inproceedings{B2021,
  author = {Beta, B},
  title = {Title B},
  booktitle = {Conf},
  year = {2021},
  pages = {6--10},
}
"""
    result = bibtex_cleaner(bib, DEFAULT_OPTION)
    assert "A2021" in result
    assert "B2021" in result


def test_cleaner():
    bibtext = """
@article{Watts1998,
annote = {10.1038/30918},
author = {Watts, Duncan J and Strogatz, Steven H},
file = {:C\\:/Users/shiori/OneDrive/Mendeley/1998/Watts, Strogatz - 1998 - Collective dynamics of `small-world' networks.pdf:pdf},
issn = {0028-0836},
journal = {Nature},
month = {jun},
number = {6684},
pages = {440--442},
title = {{Collective dynamics of `small-world' networks}},
url = {http://dx.doi.org/10.1038/30918},
volume = {393},
year = {1998}
}
    """
    option = {'savetitlecase': True, 'replaceid': False, 'jauthor': False, 'revjauthor': False}
    ret = bibtex_cleaner(bibtext, option)
    cleaned = "@article{Watts1998,\n  author = {Watts, Duncan J and Strogatz, Steven H},\n  journal = {Nature},\n  number = {6684},\n  pages = {440--442},\n  title = {{Collective dynamics of `small-world' networks}},\n  volume = {393},\n  year = {1998}\n}\n"
    assert ret == cleaned


SORT_BIB = """
@misc{Zeta2020,
  author = {Zeta, Z},
  title = {Z},
  year = {2020},
}
@misc{Alpha2021,
  author = {Alpha, A},
  title = {A},
  year = {2021},
}
"""


def test_bibtex_cleaner_sort_default_is_input():
    result = bibtex_cleaner(SORT_BIB, DEFAULT_OPTION)
    assert result.index("Zeta2020") < result.index("Alpha2021")


def test_bibtex_cleaner_sort_id():
    result = bibtex_cleaner(SORT_BIB, {**DEFAULT_OPTION, "sort": "id"})
    assert result.index("Alpha2021") < result.index("Zeta2020")


def test_bibtex_cleaner_sort_input():
    result = bibtex_cleaner(SORT_BIB, {**DEFAULT_OPTION, "sort": "input"})
    assert result.index("Zeta2020") < result.index("Alpha2021")


# ---------------------------------------------------------------------------
# 残す・消すフィールドの選択 (#12)
# ---------------------------------------------------------------------------

ARTICLE_ENTRY = {
    "ID": "orig",
    "ENTRYTYPE": "article",
    "author": ["Smith, John"],
    "title": "A Title",
    "journal": "Nature",
    "year": "2020",
    "number": "2",
    "doi": "10.1234/test",
    "url": "https://example.com",
    "publisher": "Springer",
}


def _with_fields(add=None, remove=None, **kwargs):
    return {**BASE_OPTION, **kwargs, "fields": {"add": add or {}, "remove": remove or {}}}


def test_clean_entry_add_field_for_type():
    result = clean_entry(dict(ARTICLE_ENTRY), _with_fields(add={"article": ["doi", "url"]}))
    assert result["doi"] == "10.1234/test"
    assert result["url"] == "https://example.com"
    assert "publisher" not in result


def test_clean_entry_add_field_other_type_has_no_effect():
    result = clean_entry(dict(ARTICLE_ENTRY), _with_fields(add={"inproceedings": ["publisher"]}))
    assert "publisher" not in result


def test_clean_entry_remove_default_field():
    result = clean_entry(dict(ARTICLE_ENTRY), _with_fields(remove={"article": ["number"]}))
    assert "number" not in result
    assert result["journal"] == "Nature"


def test_clean_entry_removed_author_still_used_for_id():
    option = _with_fields(remove={"article": ["author", "year"]}, replaceid=True)
    result = clean_entry(dict(ARTICLE_ENTRY), option)
    assert result["ID"] == "Smith2020"
    assert "author" not in result
    assert "year" not in result


def test_clean_entry_save_doi_combined_with_fields():
    option = _with_fields(add={"article": ["url"]}, save_doi=True)
    result = clean_entry(dict(ARTICLE_ENTRY), option)
    assert "doi" in result
    assert "url" in result


def test_clean_entry_default_proceedings_id_unchanged():
    # proceedingsは既定でauthorを残さないので、従来どおりIDは置換されない
    entry = {"ID": "orig", "ENTRYTYPE": "proceedings", "author": ["Smith, John"], "title": "T", "year": "2020"}
    result = clean_entry(entry, {**BASE_OPTION, "replaceid": True})
    assert result["ID"] == "orig"
    assert "author" not in result


def test_sanitize_field_settings_filters_invalid_values():
    data = {
        "add": {"article": ["DOI", " url ", "bad name", 1, "doi"], "unknowntype": ["doi"], "book": "doi"},
        "remove": {"article": ["note"]},
        "other": {},
    }
    assert sanitize_field_settings(data) == {
        "add": {"article": ["doi", "url"]},
        "remove": {"article": ["note"]},
    }


@pytest.mark.parametrize("data", [None, [], "x", {"add": []}, {"add": {"article": None}}])
def test_sanitize_field_settings_malformed(data):
    assert sanitize_field_settings(data) == {"add": {}, "remove": {}}


def test_parse_field_list_all_types_and_specific_type():
    result = parse_field_list("doi, inproceedings:Publisher")
    assert set(result) == set(required_fields)
    assert result["article"] == ["doi"]
    assert result["inproceedings"] == ["doi", "publisher"]


@pytest.mark.parametrize("text", ["bad name!", "nosuchtype:doi", "article:"])
def test_parse_field_list_invalid(text):
    with pytest.raises(ValueError):
        parse_field_list(text)


def test_bibtex_cleaner_with_field_settings():
    option = {**DEFAULT_OPTION, "fields": {"add": {"inproceedings": ["doi"]}, "remove": {"inproceedings": ["pages"]}}}
    result = bibtex_cleaner(INPROCEEDINGS_BIB, option)
    assert "doi = {10.1234/foo}" in result
    assert "pages" not in result


def test_bibtex_cleaner_mastersthesis():
    # BibTeXの標準タイプ名は mastersthesis（masterthesis ではない）
    bib = "@mastersthesis{x, author={Doe, John}, title={T}, school={S}, year={2020}, url={u}}"
    result = bibtex_cleaner(bib, DEFAULT_OPTION)
    assert result.startswith("@mastersthesis{x,")
    assert "school = {S}" in result
    assert "url" not in result
