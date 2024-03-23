from flask import Flask, render_template, request, redirect, flash, get_flashed_messages, url_for
from dotenv import load_dotenv
import psycopg2
from datetime import date
from urllib.parse import urlparse
from validators.url import url
from bs4 import BeautifulSoup
import requests

import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'test_secret_key')
load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')


def connect_to_database():
    return psycopg2.connect(DATABASE_URL)


def normalize_url(url_name):
    parsed_url = urlparse(url_name)
    normalized_url = f'{parsed_url.scheme}://{parsed_url.netloc}'

    return normalized_url


def is_duplicate(url_name):
    conn = connect_to_database()
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM urls WHERE name='{url_name}';")
    row = cur.fetchall()
    cur.close()
    if row:
        return row[0][0]


def get_response(url_name):
    try:
        response = requests.get(url_name, timeout=1)
        response.raise_for_status()
    except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.RequestException):
        return None
    return response


def get_info(response):
    soup = BeautifulSoup(response.text, 'html.parser')
    title = soup.find('title')
    title = title.get_text() if title else ''
    h1 = soup.find('h1')
    h1 = h1.get_text() if h1 else ''
    meta_description = soup.find('meta', attrs={"name": "description"})
    meta_content = ''
    if meta_description:
        meta_content = meta_description.get('content', '')
    return title, h1, meta_content


def get_site(url_id):
    conn = connect_to_database()
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM urls WHERE id={url_id};")
    site_info = cur.fetchone()
    cur.close()
    return site_info


@app.route('/')
def main():
    messages = get_flashed_messages(with_categories=True)
    return render_template(
        'index.html',
        messages=messages
    )


@app.route('/urls')
def urls_list():
    conn = connect_to_database()
    cur = conn.cursor()
    cur.execute("SELECT * FROM urls ORDER BY id DESC;")
    rows = cur.fetchall()
    sites = {}
    for row in rows:
        query = f"""SELECT url_checks.created_at, url_checks.status_code FROM url_checks
                   INNER JOIN urls on urls.id=url_checks.url_id
                   WHERE url_checks.url_id={row[0]}
                   ORDER BY url_checks.id DESC
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
    conn = connect_to_database()
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM urls WHERE id={url_id};")
    site_info = cur.fetchall()
    cur.execute(f"SELECT * FROM url_checks WHERE url_id={url_id} ORDER BY id DESC;")
    rows_check = cur.fetchall()
    cur.close()
    messages = get_flashed_messages(with_categories=True)
    return render_template(
        'site.html',
        site=site_info[0],
        checks=rows_check,
        messages=messages
    )


@app.post('/urls')
def add_url():
    conn = connect_to_database()
    url_name = request.form.get('url', '')
    if not url(url_name) or len(url_name) > 255:
        flash('Некорректный URL', 'danger')
        return redirect(url_for('main'), code=422)
    url_name = normalize_url(url_name)
    url_id = is_duplicate(url_name)
    if url_id:
        flash('Страница уже существует', 'info')
        return redirect(url_for('get_url', url_id=url_id))
    cur = conn.cursor()
    query = f"INSERT INTO urls (name, created_at) VALUES ('{url_name}', '{date.today()}');"
    try:
        cur.execute(query)
    except psycopg2.Error:
        raise
    finally:
        conn.commit()
    cur.execute(f"SELECT id FROM urls WHERE name='{url_name}';")
    url_id = cur.fetchone()[0]
    cur.close()
    flash('Страница успешно добавлена', 'success')
    return redirect(url_for('get_url', url_id=url_id))


@app.post('/urls/<int:url_id>/checks')
def check_url(url_id):
    conn = connect_to_database()
    cur = conn.cursor()
    site_info = get_site(url_id)
    response = get_response(site_info[1])
    if response is None:
        flash('Произошла ошибка при проверке', 'danger')
        return redirect(url_for('get_url', url_id=url_id))
    title, h1, meta_content = get_info(response)
    create_query = f"INSERT INTO url_checks (url_id, status_code, h1, title, description, created_at) " \
                   f"VALUES ('{url_id}', '{response.status_code}','{h1}','{title}','{meta_content}', '{date.today()}');"
    try:
        cur.execute(create_query)
    except psycopg2.Error:
        raise
    finally:
        conn.commit()
        cur.close()
    flash('Страница успешно проверена', 'success')
    return redirect(url_for('get_url', url_id=url_id))


if __name__ == '__main__':
    app.run(debug=True)
