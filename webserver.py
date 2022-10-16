from threading import Thread
import os
import requests
import time

from flask import Flask, render_template, request

app = Flask('', static_url_path='')
url = "https://Kozlovskiy.comrsmaster.repl.co/"


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/check')
def check():
    return {"images": os.listdir("static/i/")}


@app.route('/upload/<file_id>', methods=['POST'])
def user(file_id):
    if request.method == 'POST':
        with open("static/i/" + file_id + ".jpg", 'wb') as new_photo:
            new_photo.write(request.data)


def run():
    app.run(host='0.0.0.0', port=8080)


def ping():
    while True:
        requests.head(url)
        time.sleep(150)


def keep_alive(is_local):
    Thread(target=run).start()
    if not is_local:
        Thread(target=ping).start()
