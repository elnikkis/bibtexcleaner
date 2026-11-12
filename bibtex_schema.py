# 各エントリタイプで既定で残すフィールド
# 方針: 文献の特定に必要なもの（著者・題・掲載先・年・巻号頁）を残し、
# スタイルによって出たり出なかったりして体裁を崩しやすいもの
# （month, note, organization, doi, url, 会議の開催地・出版社・編者）は落とす。
# ただし、それがないと文献を特定できないもの（編著書のeditor、miscのurl、
# unpublishedのnote）や、出版地としてのaddress（book, thesis, techreportなど）は残す。
# 標準のフィールド一覧は https://ja.wikipedia.org/wiki/BibTeX を参照
_inproceedings = ["author", "title", "booktitle", "year", "pages", "key"]
_thesis = ["author", "title", "school", "address", "year", "key"]

required = {
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
    "inproceedings": list(_inproceedings),
    "phdthesis": list(_thesis),
    "mastersthesis": list(_thesis),
    "proceedings": [
        "editor",
        "title",
        "year",
        "publisher",
        "volume",
        "number",
        "series",
        "key",
    ],
    # BibTeXでは@conferenceは@inproceedingsの別名なので同じにする
    "conference": list(_inproceedings),
    "book": [
        "author",
        "editor",
        "title",
        "publisher",
        "address",
        "year",
        "volume",
        "series",
        "edition",
        "key",
    ],
    "booklet": [
        "author",
        "title",
        "howpublished",
        "address",
        "year",
        "key",
    ],
    "inbook": [
        "author",
        "editor",
        "title",
        "chapter",
        "pages",
        "publisher",
        "address",
        "year",
        "volume",
        "series",
        "edition",
        "key",
    ],
    "incollection": [
        "author",
        "title",
        "booktitle",
        "editor",
        "publisher",
        "address",
        "year",
        "pages",
        "key",
    ],
    "manual": [
        "author",
        "title",
        "organization",
        "address",
        "edition",
        "year",
        "key",
    ],
    "techreport": [
        "author",
        "title",
        "institution",
        "type",
        "number",
        "address",
        "year",
        "key",
    ],
    # miscはウェブページ・ソフトウェア・データセット・arXivなどに使われ、urlがないと特定できない
    "misc": ["author", "title", "howpublished", "year", "note", "url", "key"],
    # unpublishedではnoteが必須フィールド
    "unpublished": ["author", "title", "note", "year", "key"],
    # 以下はBibLaTeXでよく使われるタイプ。
    # BibLaTeX形式のエクスポートではyearの代わりにdateが入ることが多いので両方残す。
    "online": ["author", "title", "organization", "year", "date", "url", "urldate", "key"],
    # software・datasetではDOI（Zenodoなど）が主な識別子になる
    "software": [
        "author",
        "title",
        "version",
        "organization",
        "publisher",
        "year",
        "date",
        "url",
        "doi",
        "key",
    ],
    "dataset": [
        "author",
        "title",
        "version",
        "publisher",
        "year",
        "date",
        "url",
        "doi",
        "key",
    ],
}

# 「全タイプ一括」で残す・消すを切り替えられるようにするフィールド
common = ["doi", "url", "isbn", "month", "note", "key", "publisher", "address", "editor"]

# フィールド追加入力の候補（自由入力も可能）
suggestions = sorted(
    {field for fields in required.values() for field in fields}
    | set(common)
    | {"articleno", "numpages", "issn", "eprint", "archiveprefix", "primaryclass", "urldate", "language"}
)
