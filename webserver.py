from threading import Thread

from flask import Flask

app = Flask('')
current_image = b""


@app.route('/')
def home():
    return "Монитор активен."


def run():
    app.run(host='0.0.0.0', port=8080)


def keep_alive():
    t = Thread(target=run)
    t.start()
