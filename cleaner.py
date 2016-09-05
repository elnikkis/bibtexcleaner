# coding: utf-8

"""
BibTexのいらない項目を削除するスクリプト

問題：
IDが重複している恐れがある
"""

import sys
import bibtexparser
from bibtexparser.bibdatabase import BibDatabase
from bibtexparser.bwriter import BibTexWriter

# from Wikipedia (https://ja.wikipedia.org/wiki/BibTeX)
nessesary = {
    #'article': ['author', 'title', 'journal', 'year', 'volume', 'number', 'pages', 'month', 'note', 'key'],
    'article': ['author', 'title', 'journal', 'year', 'volume', 'number', 'pages', 'key'],
    'phdthesis': ['author', 'title', 'school', 'year', 'address', 'month', 'note', 'key'],
    'masterthesis': ['author', 'title', 'school', 'year', 'address', 'month', 'note', 'key'],
    'proceedings': ['title', 'year', 'editor', 'publisher', 'organization', 'address', 'month', 'note', 'key'],
#    'inproceedings': ['author', 'title', 'booktitle', 'year', 'editor', 'pages', 'organization', 'publisher', 'address', 'month', 'note', 'key'],
    'inproceedings': ['author', 'title', 'booktitle', 'year', 'pages', 'key'],
    'conference': ['author', 'title', 'booktitle', 'year', 'editor', 'pages', 'organization', 'publisher', 'address', 'month', 'note', 'key'],
    'book': ['author', 'editor', 'title', 'publisher', 'year', 'volume', 'series', 'address', 'edition', 'month', 'note', 'key'],
    'booklet': ['title', 'author', 'howpublished', 'address', 'month', 'year', 'note', 'key'],
    'inbook': ['author', 'editor', 'title', 'chapter', 'pages', 'publisher', 'year', 'volume', 'series', 'address', 'edition', 'month', 'note', 'key'],
    'incollection': ['author', 'title', 'booktitle', 'year', 'editor', 'pages', 'organization', 'publisher', 'address', 'month', 'note', 'key'],
    'manual': ['title', 'author', 'organization', 'address', 'edition', 'month', 'year', 'note', 'key'],
    'techreport': ['author', 'title', 'institution', 'year', 'type', 'number', 'address', 'month', 'note', 'key'],
    'misc': ['author', 'title', 'howpublished', 'month', 'year', 'note', 'key'],
    'unpublished': ['author', 'title', 'note', 'month', 'year', 'key']
}

def is_japanese(string):
    for c in string:
        name = unicodedata.name(c)
        if('CJK UNIFIED' in name or
           'HIRAGANA' in name or
           'KATAKANA' in name):
            return True
    return False


def make_id(entry):
    # authorが含まれていないエントリーはIDを変更しない
    if 'author' not in entry or 'year' not in entry:
        return entry['ID']

    idx = entry['author'].find(',')
    if idx == -1:
        name = entry['author']
    else:
        name = entry['author'][0:idx]

    # exclude spaces
    name = name.replace(' ', '').replace('.', '').replace('{', '').replace('}', '')

    return name + entry['year']

def clean_entries(bib_database):
    cleaned = []
    for entry in bib_database.entries:
        needs = nessesary[entry['ENTRYTYPE']]
        e = {}
        e['ENTRYTYPE'] = entry['ENTRYTYPE']
        e['ID'] = make_id(entry)
        for item in entry.keys():
            if item in needs:
                e[item] = entry[item]
        cleaned.append(e)

    # titleを{}でかこむ (caseを保存するため)
    for entry in cleaned:
        entry['title'] = '{' + entry['title'] + '}'

    # make new db
    db = BibDatabase()
    db.entries = cleaned
    return db

def parse_args():
    import argparse
    parser = argparse.ArgumentParser(description='Bibtex cleaner')
    parser.add_argument('bibfile', type=argparse.FileType('r'),
                        help='汚いbibファイル（入力ファイル名）')
    parser.add_argument('outfile', nargs='?', type=argparse.FileType('w'), default=sys.stdout,
                        help='きれいなbibファイル名（出力ファイル名; default: stdout）')
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()
    bibtex_str = args.bibfile.read()
    bib_database = bibtexparser.loads(bibtex_str)
    cleaned_database = clean_entries(bib_database)
    #print(bib_database.entries)
    #print(cleaned_database.entries)
    writer = BibTexWriter()
    args.outfile.write(writer.write(cleaned_database))
