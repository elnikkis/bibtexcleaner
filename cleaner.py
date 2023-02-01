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


def parser_customizations(record):
    record = bcus.author(record)
    record = bcus.page_double_hyphen(record)
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
    name = name_dict["last"][0]

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
            name_dict = splitname(fullname, strict_mode=False)
            if name_dict["von"] or name_dict["jr"] or not _is_japanese(fullname):
                # 日本人の名前にはvonやjrはないはず
                # 日本人の名前以外はそのまま
                name = fullname
            elif reverse_author:
                name = name_dict["first"] + " " + name_dict["last"]
            else:
                name = name_dict["last"] + " " + name_dict["first"]
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
        writer.indent = '  '
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
