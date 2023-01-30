# coding: utf-8
"""
BibTexのいらない項目を削除するスクリプト
"""

import sys
import re
import unicodedata
from collections import Counter
import bibtexparser
from bibtexparser.bibdatabase import BibDatabase
from bibtexparser.bwriter import BibTexWriter


class Setting:
    items = ["savetitlecase", "replaceid", "jauthor", "revjauthor"]


# from Wikipedia (https://ja.wikipedia.org/wiki/BibTeX)
necessary = {
    "article": [
        "author",
        "title",
        "journal",
        "year",
        "volume",
        "number",
        "pages",
        "key",
    ],
    "phdthesis": [
        "author",
        "title",
        "school",
        "year",
        "address",
        "month",
        "note",
        "key",
    ],
    "masterthesis": [
        "author",
        "title",
        "school",
        "year",
        "address",
        "month",
        "note",
        "key",
    ],
    "proceedings": [
        "title",
        "year",
        "editor",
        "publisher",
        "organization",
        "address",
        "month",
        "note",
        "key",
        "volume",
        "number",
    ],
    "inproceedings": ["author", "title", "booktitle", "year", "pages", "key"],
    "conference": [
        "author",
        "title",
        "booktitle",
        "year",
        "editor",
        "pages",
        "organization",
        "publisher",
        "address",
        "month",
        "note",
        "key",
    ],
    "book": [
        "author",
        "editor",
        "title",
        "publisher",
        "year",
        "volume",
        "series",
        "address",
        "edition",
        "month",
        "note",
        "key",
    ],
    "booklet": [
        "title",
        "author",
        "howpublished",
        "address",
        "month",
        "year",
        "note",
        "key",
    ],
    "inbook": [
        "author",
        "editor",
        "title",
        "chapter",
        "pages",
        "publisher",
        "year",
        "volume",
        "series",
        "address",
        "edition",
        "month",
        "note",
        "key",
    ],
    "incollection": [
        "author",
        "title",
        "booktitle",
        "year",
        "editor",
        "pages",
        "organization",
        "publisher",
        "address",
        "month",
        "note",
        "key",
    ],
    "manual": [
        "title",
        "author",
        "organization",
        "address",
        "edition",
        "month",
        "year",
        "note",
        "key",
    ],
    "techreport": [
        "author",
        "title",
        "institution",
        "year",
        "type",
        "number",
        "address",
        "month",
        "note",
        "key",
    ],
    "misc": ["author", "title", "howpublished", "month", "year", "note", "key"],
    "unpublished": ["author", "title", "note", "month", "year", "key"],
}


def print_necessary_as_html():
    fd = sys.stdout
    print("<dl>", file=fd)
    for key, value in necessary.items():
        print("<dt>%s</dt>" % key, file=fd)
        for field in value:
            print("<dd>%s</dd>" % field, file=fd)
    print("</dl>", file=fd)


def is_japanese(string):
    for c in string:
        name = unicodedata.name(c)
        if "CJK UNIFIED" in name or "HIRAGANA" in name or "KATAKANA" in name:
            return True
    return False


def make_id(entry):
    # authorが含まれていないエントリーはIDを変更しない
    if "author" not in entry or "year" not in entry or not entry["author"]:
        return entry["ID"]
    name = entry["author"].split("and")[0].strip().split()[0].strip(",")
    # exclude spaces
    name = name.replace(" ", "").replace(".", "").replace("{", "").replace("}", "")

    return name + entry["year"]


def clean_entries(bib_database, option):
    cleaned = []
    for entry in bib_database.entries:
        # 必要なフィールドだけ取り出す
        needs = necessary[entry["ENTRYTYPE"]]
        e = {}
        e["ID"] = entry["ID"]
        e["ENTRYTYPE"] = entry["ENTRYTYPE"]
        for item in entry.keys():
            if item in needs:
                e[item] = entry[item]

        # 日本人ぽいauthorは姓名のあいだの,を消す
        if option["jauthor"] and "author" in e and is_japanese(e["author"]):
            names = []
            for fullname in entry["author"].split("and"):
                name = [name.strip() for name in fullname.split(",")]
                if option["revjauthor"]:
                    name = reversed(name)
                names.append(" ".join(name))
            e["author"] = " and ".join(names)

        # titleを{}でかこむ (caseを保存するため)
        if option["savetitlecase"] and "title" in entry:
            e["title"] = "{%s}" % e["title"]

        # 引用keyをauthor+yearで置き換える
        if option["replaceid"]:
            e["ID"] = make_id(e)
        cleaned.append(e)

    # keyが同じentryをuniqueにする
    counter = Counter([entry["ID"] for entry in cleaned])
    for key, count in counter.items():
        if count >= 2:
            cnt = 0
            for entry in cleaned:
                if entry["ID"] == key:
                    entry["ID"] = entry["ID"] + chr(ord("a") + cnt)
                    cnt += 1

    # make new db
    db = BibDatabase()
    db.entries = cleaned
    return db


def parse_args():
    import argparse

    parser = argparse.ArgumentParser(description="Bibtex cleaner")
    parser.add_argument(
        "bibfile",
        type=argparse.FileType("r"),
        help="汚いbibファイル（入力ファイル名; default: stdin）",
        default=sys.stdin,
        nargs="?",
    )
    parser.add_argument(
        "outfile",
        nargs="?",
        type=argparse.FileType("w"),
        default=sys.stdout,
        help="きれいなbibファイル名（出力ファイル名; default: stdout）",
    )
    return parser.parse_args()


def bibtex_cleaner(bibtext, option):
    try:
        bib_database = bibtexparser.loads(bibtext)
        cleaned_database = clean_entries(bib_database, option)
        writer = BibTexWriter()
        return writer.write(cleaned_database)
    except Exception:
        return "Error. 入力形式はbibtexですか？（または変換プログラムのバグの可能性があります）\n"


if __name__ == "__main__":
    args = parse_args()
    bibtex_str = args.bibfile.read()
    args.outfile.write(bibtex_cleaner(bibtex_str))
