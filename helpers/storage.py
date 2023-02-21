import json

import requests

from helpers.config import is_dev, fb_url

with open('db.json', encoding="utf-8") as bd_file:
    bd = json.load(bd_file)

ignore: list = bd['ignore']
images: dict = bd['images']
current_chat = bd['current_chat']
users: dict[str, dict] = bd['users']
abstracts: dict[str, dict] = bd['abstracts']
chat_id_my = bd['chat_id_my']
chat_id_pen: list = bd['chat_id_pen']
chat_msg_my = bd['chat_msg_my']
chat_msg_pen = bd['chat_msg_pen']
current_users = bd['current_users']


def save():
    to_save = json.dumps(bd, ensure_ascii=False)
    with open('db.json', 'w', encoding='utf-8') as db_file1:
        db_file1.write(to_save)
    if not is_dev:
        requests.put(f'{fb_url}.json', data=to_save.encode("utf-8"),
                     headers={"content-type": "application/json; charset=UTF-8"})
