from threading import Thread
import os

from flask import Flask, render_template, request

app = Flask('')


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/check')
def check():
    return {"images": os.listdir("static/")}


@app.route('/upload/<file_id>', methods=['POST'])
def user(file_id):
    if request.method == 'POST':
        with open("static/" + file_id + ".jpg", 'wb') as new_photo:
            new_photo.write(request.data)


def run():
    app.run(host='0.0.0.0', port=8080)


def keep_alive():
    t = Thread(target=run)
    t.start()


if __name__ == "__main__":
    keep_alive()
