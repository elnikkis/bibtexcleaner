# coding: utf-8

from cleaner import bibtex_cleaner
from flask import Flask, render_template, request, Response, abort

app = Flask(__name__)


def clean_bibtext(bibtext):
    cleaned = bibtex_cleaner(bibtext)
    return cleaned


@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/clean', methods=['POST'])
def clean():
    if request.method == 'POST':
        if 'bibtex' in request.form:
            bibtext = request.form['bibtex']
        elif 'bibtex' in request.files:
            bibtext = request.files['bibtex'].read().decode('utf-8')
            if not bibtext:
                abort(400)
        else:
            # error
            abort(400)
        cleaned = clean_bibtext(bibtext)
        return Response(cleaned, mimetype='text/plain')

if __name__ == '__main__':
    app.debug = True
    app.run()
