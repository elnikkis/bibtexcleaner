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
from bibtexparser.bparser import BibTexParser
from bibtexparser.bwriter import BibTexWriter
from bibtexparser.customization import splitname
import bibtexparser.customization as bcus

from bibtex_schema import required as required_fields


def page_double_hyphen(record):
    """
    Separate pages by a double hyphen (--).

    Args:
        record (dict): the record
    Returns:
        dict: the modified record
    """
    if "pages" in record:
        # double-hyphen, hyphen, non-breaking hyphen, en dash, em dash, hyphen-minus, minus sign
        separators = ["--", "‐", "‑", "–", "—", "-", "−"]
        for separator in separators:
            if separator in record["pages"]:
                p = [
                    i.strip().strip(separator)
                    for i in record["pages"].split(separator, 1)
                ]
                record["pages"] = p[0] + "--" + p[-1]
                return record
    return record


def split_author(record):
    if "author" in record and record["author"]:
        record["author"] = [
            fullname.strip() for fullname in record["author"].split(" and ")
        ]
    return record


def remove_line_breaks(record):
    target_fields = ["author", "title", "journal", "booktitle"]
    table = str.maketrans("\n\r", "  ")
    for key in target_fields:
        if key in record and isinstance(record[key], str):
            record[key] = record[key].translate(table)
        if key in record and isinstance(record[key], list):
            record[key] = [
                item.translate(table) if isinstance(item, str) else item
                for item in record[key]
            ]
    return record


def parser_customizations(record):
    record = bcus.type(record)
    record = remove_line_breaks(record)
    record = split_author(record)
    record = page_double_hyphen(record)
    return record


class CleanerException(Exception):
    pass


def print_required_fields_as_html():
    """Cleanerが残すフィールド定義辞書の中身を出力する"""
    fd = sys.stdout
    print("<dl>", file=fd)
    for key, value in required_fields.items():
        print("<dt>%s</dt>" % key, file=fd)
        for field in value:
            print("<dd>%s</dd>" % field, file=fd)
    print("</dl>", file=fd)


def _is_japanese(string):
    """文字列が日本語かを判定する

    Args:
        string (str): 判定する文字列

    Returns:
        bool: 日本語範囲のUnicodeが1文字でも含まれていればTrueを返す。
    """
    for c in string:
        try:
            name = unicodedata.name(c)
        except ValueError:
            # control characterの可能性がある。無視する
            return False
        if "CJK UNIFIED" in name or "HIRAGANA" in name or "KATAKANA" in name:
            return True
    return False


def _make_id(entry):
    """entryからauthorとyearフィールドの中身を使って新たなIDを生成する

    Args:
        entry: bibtexエントリ

    Returns:
        str: authorとyearから生成されたID（例：Author2010）
    """
    # authorが含まれていないエントリーはIDを変更しない
    if "author" not in entry or "year" not in entry or not entry["author"]:
        return entry["ID"]

    first_author = entry["author"][0]
    name_dict = splitname(first_author)

    # firstもlastも空ならなにもしない
    if not name_dict["first"] and not name_dict["last"]:
        return entry["ID"]

    if not name_dict["first"] or not name_dict["last"]:
        # firstかlastのどちらかが空ならある方を使う
        if name_dict["last"]:
            name = "".join(name_dict["last"])
        else:
            name = "".join(name_dict["first"])
    elif _is_japanese(first_author):
        # 日本人名は入れ替え済みなのでfirst
        name = "".join(name_dict["first"])
    else:
        # 基本的にはlast
        name = "".join(name_dict["last"])

    # exclude spaces
    name = name.replace(" ", "").replace(".", "").replace("{", "").replace("}", "")
    return name + entry["year"]


def check_parentheses_matching(string, opening, closing):
    """openingとclosingが対応しているか調べる

    Args:
        opening (str):
        closing (str):

    Returns:
        bool: openingとclosingが対応していればTrueを返す
    """
    opening = set(opening)
    closing = set(closing)

    stack = []
    for c in string:
        if c in opening:
            stack.append(c)
        elif c in closing:
            try:
                stack.pop()
            except IndexError:
                # popする要素がない
                return False

    if len(stack) > 0:
        # マッチしていない括弧が残っている
        return False
    else:
        return True


def _wrap_title(entry):
    if "title" in entry:
        title = entry["title"]
        if (
            title[0] == "{"
            and title[-1] == "}"
            and check_parentheses_matching(title[1:-1], "{", "}")
        ):
            # 先頭と末尾にマッチする括弧がすでに存在するのでなにもしない
            return entry
        entry["title"] = "{%s}" % entry["title"]
    return entry


def _treat_japanese_author(entry, reverse_author: bool):
    if "author" in entry:
        names = []
        for fullname in entry["author"]:
            if _is_japanese(fullname) and "," in fullname:
                last, first = fullname.split(",", 1)
                first = first.strip()
                last = last.strip()
                if reverse_author:
                    name = f"{first} {last}"
                else:
                    name = f"{last} {first}"
            else:
                # 日本人の名前以外はそのまま
                name = fullname
            names.append(name)
        entry["author"] = names
    return entry


def clean_entry(entry, option):
    # 必要なフィールドだけ取り出す
    try:
        needs = required_fields[entry["ENTRYTYPE"]]
    except KeyError:
        raise CleanerException(f"Unknown entry type: {entry['ENTRYTYPE']}")
    e = {}
    e["ID"] = entry["ID"]
    e["ENTRYTYPE"] = entry["ENTRYTYPE"]
    for item in entry.keys():
        if item in needs:
            e[item] = entry[item]

    # 日本人ぽいauthorは姓名のあいだの,を消す
    if option["jauthor"]:
        e = _treat_japanese_author(e, reverse_author=option["revjauthor"])
        pass

    # titleを{}でかこむ (caseを保存するため)
    if option["savetitlecase"]:
        e = _wrap_title(e)

    # 引用keyをauthor+yearで置き換える
    if option["replaceid"]:
        e["ID"] = _make_id(e)

    # authorをlistからstrに戻す
    e["author"] = " and ".join(e["author"])
    return e


def clean_entries(bib_database, option):
    """
    きれいにする

    Args:
        bib_database (BibDatabase):
        option (dict):

    Returns:
        BibDatabase:
    """
    cleaned_entries = []
    for entry in bib_database.entries:
        e = clean_entry(entry, option)
        cleaned_entries.append(e)

    # keyが同じentryをuniqueにする
    counter = Counter([entry["ID"] for entry in cleaned_entries])
    for key, count in counter.items():
        if count >= 2:
            cnt = 0
            for entry in cleaned_entries:
                if entry["ID"] == key:
                    entry["ID"] = entry["ID"] + chr(ord("a") + cnt)
                    cnt += 1

    # make new db
    db = BibDatabase()
    db.entries = cleaned_entries
    return db


def bibtex_cleaner(bibtext, option):
    """BibTeXを読み込み、きれいな形に整形して返す

    Args:
        bibtext (str): BibTexの文字列
        option (dict): クリーナーの設定

    Returns:
        str: 整形されたBibTex
    """
    try:
        parser = BibTexParser(customization=parser_customizations)
        bib_database = bibtexparser.loads(bibtext, parser=parser)
        cleaned_database = clean_entries(bib_database, option)
        writer = BibTexWriter()
        writer.indent = "  "
        return writer.write(cleaned_database)
    except CleanerException as e:
        raise


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


if __name__ == "__main__":
    args = parse_args()
    bibtex_str = args.bibfile.read()
    args.outfile.write(bibtex_cleaner(bibtex_str))
