# coding: utf-8

import json

from flask import Flask, render_template, request, Response, abort
from cleaner import (
    bibtex_cleaner,
    CleanerException,
    SORT_ORDERS,
    sanitize_field_settings,
)
import bibtex_schema

# フィールド設定（JSON）として受け付ける最大長
MAX_FIELDS_JSON_LENGTH = 100_000

app = Flask(__name__)


class Setting:
    # save_doiは旧フォームとの互換のため受け付ける（現在のUIではfieldsで指定する）
    items = ["savetitlecase", "replaceid", "jauthor", "revjauthor", "save_doi"]


def parse_fields_option(text):
    """フォームの "fields"（既定からの差分のJSON）を解釈する。不正なら差分なし"""
    if not text or len(text) > MAX_FIELDS_JSON_LENGTH:
        return sanitize_field_settings(None)
    try:
        data = json.loads(text)
    except ValueError:
        data = None
    return sanitize_field_settings(data)


@app.route("/")
def index():
    return render_template(
        "index.html",
        # tojsonは辞書のキーをソートしてしまうので、表示順を保つため[type, fields]の列で渡す
        schema=list(bibtex_schema.required.items()),
        common_fields=bibtex_schema.common,
        field_suggestions=bibtex_schema.suggestions,
    )


@app.route("/clean", methods=["POST"])
def clean():
    if request.method == "POST":
        if "fromtext" in request.form and "bibtext" in request.form:
            bibtext = request.form["bibtext"]
        elif "fromfile" in request.form and "bibfile" in request.files:
            try:
                bibtext = request.files["bibfile"].read().decode("utf-8")
            except UnicodeDecodeError:
                return Response(
                    "Error. ファイルの文字コードがUTF-8ではありません\n",
                    mimetype="text/plain",
                )
        else:
            # error
            abort(400)

        # エラー処理
        if bibtext is None:
            abort(400)
        if bibtext == "":
            return Response("Error. 入力が空です", mimetype="text/plain")

        # 設定を取り出す
        option = {}
        for opt in Setting.items:
            if request.form.get(opt) == "on":
                option[opt] = True
            else:
                option[opt] = False
        sort = request.form.get("sort", "input")
        option["sort"] = sort if sort in SORT_ORDERS else "input"
        option["fields"] = parse_fields_option(request.form.get("fields"))

        try:
            cleaned = bibtex_cleaner(bibtext, option)
        except Exception as e:
            if not isinstance(e, CleanerException):
                # 想定外の例外はサーバーログに残し、クライアントには詳細を返さない
                app.logger.exception("bibtex_cleaner failed")
            return Response(
                "Error. 入力形式はbibtexですか？（または変換プログラムのバグの可能性があります）\n",
                mimetype="text/plain",
            )

        return Response(cleaned, mimetype="text/plain")


@app.route("/healthz")
def health_check():
    return Response('fine', mimetype="text/plain")

if __name__ == "__main__":
    app.debug = True
    app.run()
