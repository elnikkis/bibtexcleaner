# coding: utf-8

from cleaner import bibtex_cleaner, Setting
from flask import Flask, render_template, request, Response, abort, render_template

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/clean', methods=['POST'])
def clean():
    if request.method == 'POST':
        if 'fromtext' in request.form and 'bibtext' in request.form:
            bibtext = request.form['bibtext']
        elif 'fromfile' in request.form and 'bibfile' in request.files:
            bibtext = request.files['bibfile'].read().decode('utf-8')
        else:
            # error
            abort(400)

        # エラー処理
        if bibtext is None:
            abort(400)
        if bibtext == '':
            return Response('Error. 入力が空です', mimetype='text/plain')

        # 設定を取り出す
        option = {}
        for opt in Setting.items:
            if request.form.get(opt) == 'on':
                option[opt] = True
            else:
                option[opt] = False

        cleaned = bibtex_cleaner(bibtext, option)
        return Response(cleaned, mimetype='text/plain')

if __name__ == '__main__':
    app.debug = True
    app.run()
