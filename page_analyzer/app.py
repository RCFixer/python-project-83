from flask import Flask, render_template, request, redirect, flash, get_flashed_messages, url_for
from dotenv import load_dotenv
import psycopg2
from datetime import date
from urllib.parse import urlparse, urlunparse
from validators.url import url

import os

load_dotenv()
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
DATABASE_URL = os.getenv('DATABASE_URL')
conn = psycopg2.connect(DATABASE_URL + '?sslmode=disable')


def normalize_url(url_name):
    # Парсим URL
    parsed_url = urlparse(url_name)

    # Если схема (протокол) не указана, добавляем http
    if not parsed_url.scheme:
        parsed_url = parsed_url._replace(scheme='http')

    # Нормализуем URL
    normalized_url = urlunparse(parsed_url)

    return normalized_url


def is_duplicate(url_name):
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM urls WHERE name='{url_name}';")
    row = cur.fetchall()
    cur.close()
    if row:
        return row[0][0]


@app.route('/')
def main():
    messages = get_flashed_messages(with_categories=True)
    return render_template(
        'index.html',
        messages=messages
    )


@app.route('/urls')
def urls_list():
    cur = conn.cursor()
    cur.execute("SELECT * FROM urls ORDER BY id DESC;")
    rows = cur.fetchall()
    sites = {}
    for row in rows:
        query = f"""SELECT url_checks.created_at, url_checks.status_code FROM url_checks
                   INNER JOIN urls on urls.id=url_checks.url_id
                   WHERE url_checks.url_id={row[0]}
                   ORDER BY url_checks.url_id DESC
                   LIMIT 1;"""
        cur.execute(query)
        info = cur.fetchone()
        sites[row] = info if info else ('', '')
    cur.close()
    messages = get_flashed_messages(with_categories=True)
    return render_template(
        'urls.html',
        sites=sites,
        messages=messages
    )


@app.route('/urls/<int:url_id>')
def get_url(url_id):
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM urls WHERE id={url_id};")
    site_info = cur.fetchall()
    cur.execute(f"SELECT * FROM url_checks WHERE url_id={url_id} ORDER BY id DESC;")
    rows_check = cur.fetchall()
    last_check = rows_check[0][6]
    cur.close()
    messages = get_flashed_messages(with_categories=True)
    return render_template(
        'site.html',
        site=site_info[0],
        checks=rows_check,
        last_check=last_check,
        messages=messages
    )


@app.post('/urls')
def add_url():
    url_name = request.form.get('url', '')
    if not url(url_name) or len(url_name) > 255:
        flash('Некорректный URL', 'danger')
        return redirect(url_for('main'), code=302)
    url_name = normalize_url(url_name)
    url_id = is_duplicate(url_name)
    if url_id:
        flash('Страница уже существует', 'info')
        return redirect(url_for('get_url', url_id=url_id), code=302)
    cur = conn.cursor()
    query = f"INSERT INTO urls (name, created_at) VALUES ('{url_name}', '{date.today()}');"
    try:
        cur.execute(query)
    except psycopg2.Error:
        raise
    finally:
        conn.commit()
        cur.close()
    flash('Страница успешно добавлена', 'success')
    return redirect(url_for('urls_list'), code=302)


@app.post('/urls/<int:url_id>/checks')
def check_url(url_id):
    cur = conn.cursor()
    create_query = f"INSERT INTO url_checks (url_id, created_at) VALUES ('{url_id}', '{date.today()}');"
    # update_query = f"UPDATE urls SET created_at='{date.today()}' WHERE id='{url_id}';"
    try:
        cur.execute(create_query)
        # cur.execute(update_query)
    except psycopg2.Error:
        raise
    finally:
        conn.commit()
        cur.close()
    flash('Страница успешно проверена', 'success')
    return redirect(url_for('get_url', url_id=url_id), code=302)


if __name__ == '__main__':
    app.run(debug=True)
