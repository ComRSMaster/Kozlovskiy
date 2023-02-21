import requests
from bs4 import BeautifulSoup

from helpers.bot import bot


def photo_search(chat_id, msg_id, search_photo):
    bot.send_chat_action(chat_id, action="typing")
    url_pic = f"https://yandex.ru/images/search?rpt=imageview&url={bot.get_file_url(search_photo.file_id)}"
    results = BeautifulSoup(requests.get(url_pic).text, 'lxml').find('section', 'CbirTags').find_all('a')
    bot.send_message(chat_id, '\n'.join(f"• {res.find('span').get_text().capitalize()}" for res in results),
                     reply_to_message_id=msg_id)
