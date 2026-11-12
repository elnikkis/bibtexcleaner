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


# 出力エントリの並び順: "id" = ID（引用キー）順, "input" = 入力順
SORT_ORDERS = ("id", "input")

# 残す・消すフィールドとして受け付けるフィールド名
FIELD_NAME_RE = re.compile(r"[a-z][a-z0-9_.\-]*")
MAX_FIELD_NAME_LENGTH = 64
MAX_FIELDS_PER_TYPE = 50


def normalize_field_name(name):
    """フィールド名を小文字に正規化する。不正な名前ならNoneを返す"""
    if not isinstance(name, str):
        return None
    name = name.strip().lower()
    if len(name) > MAX_FIELD_NAME_LENGTH or not FIELD_NAME_RE.fullmatch(name):
        return None
    return name


def sanitize_field_settings(data):
    """既定からの差分として指定された「残す・消すフィールド」の設定を検証する

    Args:
        data: {"add": {entrytype: [field, ...]}, "remove": {entrytype: [field, ...]}}
            の形の値。外部入力なので不正な値は黙って無視する。

    Returns:
        dict: 検証済みの同じ形の辞書
    """
    result = {"add": {}, "remove": {}}
    if not isinstance(data, dict):
        return result
    for kind in ("add", "remove"):
        per_type = data.get(kind)
        if not isinstance(per_type, dict):
            continue
        for entrytype, names in per_type.items():
            if entrytype not in required_fields or not isinstance(names, list):
                continue
            fields = []
            for name in names[:MAX_FIELDS_PER_TYPE]:
                name = normalize_field_name(name)
                if name and name not in fields:
                    fields.append(name)
            if fields:
                result[kind][entrytype] = fields
    return result


def parse_field_list(text):
    """CLI用。"doi, url, inproceedings:publisher" のような指定を解釈する

    "field" は全エントリタイプ、"entrytype:field" はそのタイプだけに適用する。

    Returns:
        dict: {entrytype: [field, ...]}
    Raises:
        ValueError: 不正なフィールド名・エントリタイプが含まれる場合
    """
    result = {}
    for token in re.split(r"[,\s]+", text.strip()):
        if not token:
            continue
        if ":" in token:
            entrytype, name = token.split(":", 1)
            entrytype = entrytype.strip().lower()
            if entrytype not in required_fields:
                raise ValueError(f"Unknown entry type: {entrytype}")
            types = [entrytype]
        else:
            name = token
            types = list(required_fields)
        field = normalize_field_name(name)
        if field is None:
            raise ValueError(f"Invalid field name: {name}")
        for t in types:
            fields = result.setdefault(t, [])
            if field not in fields:
                fields.append(field)
    return result


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
        if not title:
            # 空のtitleは囲まない
            return entry
        if (
            len(title) >= 2
            and title[0] == "{"
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


def _field_sets(entrytype, option):
    """エントリタイプごとに、加工に使うフィールドと出力するフィールドを求める

    Returns:
        tuple[set, set]: (加工に使うフィールド, 出力するフィールド)
            ユーザーが既定から外したフィールド（author, yearなど）も、
            ID生成などの加工には使えるように前者には含める。
    """
    try:
        defaults = required_fields[entrytype]
    except KeyError:
        raise CleanerException(f"Unknown entry type: {entrytype}")
    settings = option.get("fields") or {}
    added = set(settings.get("add", {}).get(entrytype, ()))
    removed = set(settings.get("remove", {}).get(entrytype, ()))
    # 旧オプション: DOIフィールドを保持（CLI・APIとの互換のため残す）
    if option.get("save_doi"):
        added.add("doi")
    working = set(defaults) | added
    return working, working - removed


def clean_entry(entry, option):
    # 必要なフィールドだけ取り出す
    working, output = _field_sets(entry["ENTRYTYPE"], option)
    e = {}
    e["ID"] = entry["ID"]
    e["ENTRYTYPE"] = entry["ENTRYTYPE"]
    for item in entry.keys():
        if item in working:
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

    # 加工のためだけに残していたフィールドを取り除く
    for key in list(e.keys()):
        if key not in ("ID", "ENTRYTYPE") and key not in output:
            del e[key]

    # authorをlistからstrに戻す
    if "author" in e:
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
        if option.get("sort", "input") == "input":
            # 並び替えず入力順のまま出力する
            writer.order_entries_by = None
        else:
            writer.order_entries_by = ("ID",)
        return writer.write(cleaned_database)
    except CleanerException as e:
        raise


def parse_args():
    import argparse

    def field_list(text):
        try:
            return parse_field_list(text)
        except ValueError as e:
            raise argparse.ArgumentTypeError(str(e))

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
    parser.add_argument(
        "--sort",
        choices=SORT_ORDERS,
        default="input",
        help="出力エントリの並び順（input: 入力順, id: ID順; default: input）",
    )
    parser.add_argument(
        "--keep",
        type=field_list,
        default={},
        metavar="FIELDS",
        help="既定に加えて残すフィールド（例: doi,url,inproceedings:publisher）",
    )
    parser.add_argument(
        "--drop",
        type=field_list,
        default={},
        metavar="FIELDS",
        help="既定から取り除くフィールド（例: note,month,article:number）",
    )
    return parser.parse_args()


# Webフォームの初期値と同じ設定
DEFAULT_CLI_OPTION = {
    "savetitlecase": False,
    "replaceid": True,
    "jauthor": True,
    "revjauthor": False,
    "save_doi": False,
    "sort": "input",
}


if __name__ == "__main__":
    args = parse_args()
    bibtex_str = args.bibfile.read()
    option = {
        **DEFAULT_CLI_OPTION,
        "sort": args.sort,
        "fields": {"add": args.keep, "remove": args.drop},
    }
    args.outfile.write(bibtex_cleaner(bibtex_str, option))
