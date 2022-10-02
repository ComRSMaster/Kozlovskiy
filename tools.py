import configparser
import json
import os
import sys
import time
import traceback
from datetime import datetime
import random

import requests

if sys.version_info < (3, 9):
    # noinspection PyUnresolvedReferences,PyPackageRequirements
    from backports.zoneinfo import ZoneInfo
else:
    from zoneinfo import ZoneInfo

from importlib import util

import telebot

import webserver
from bs4 import BeautifulSoup

is_local = util.find_spec("replit") is None
del util
del sys

content_types = [
    "text", "audio", "document", "photo", "sticker", "video", "video_note",
    "voice", "location", "contact", "group_chat_created", "chat_member",
    "supergroup_chat_created", "channel_chat_created", "migrate_to_chat_id", "poll"]
config = configparser.ConfigParser()
config.read("config.ini", encoding="utf8")  # читаем конфиг
MIN_IGNORE_TIME = config.getint("Settings", "MIN_IGNORE_TIME")
MAX_IGNORE_TIME = config.getint("Settings", "MAX_IGNORE_TIME")
MIN_BIRTHDAY_HOUR = config.getint("Settings", "MIN_BIRTHDAY_HOUR")
MIN_ALLOWED_HOUR = config.getint("Settings", "MIN_ALLOWED_HOUR")
MAX_ALLOWED_HOUR = config.getint("Settings", "MAX_ALLOWED_HOUR")
admin_chat = json.loads(config["Settings"]['admin_chat'])
success_vid = json.loads(config["Settings"]['success_vid'])
starts = json.loads(config["Settings"]['starts'])
calls = json.loads(config["Settings"]['calls'])
calls_private = json.loads(config["Settings"]['calls_private'])
ends = json.loads(config["Settings"]['ends'])
searches = json.loads(config["Settings"]['searches'])
randoms = json.loads(config["Settings"]['randoms'])
ignore: list = json.loads(config["Dump"]['ignore'])
images: dict = json.loads(config["Dump"]['images'])
current_chat = config["Dump"]['current_chat']
auto_start: dict = json.loads(config["Dump"]['auto_start'])
users = json.loads(config["Dump"]['users'])
groups = json.loads(config["Dump"]['groups'])
birthdays: dict = json.loads(config["Dump"]['birthdays'])
active_goroda: list = json.loads(config["Dump"]['active_goroda'])
current_letters = json.loads(config["Dump"]['current_letters'])
wait_for_chat_id = json.loads(config["Dump"]['wait_for_chat_id'])
chat_id_my = json.loads(config["Dump"]['chat_id_my'])
chat_id_pen: list = json.loads(config["Dump"]['chat_id_pen'])
chat_msg_my = json.loads(config["Dump"]['chat_msg_my'])
chat_msg_pen = json.loads(config["Dump"]['chat_msg_pen'])
current_users = json.loads(config["Dump"]['current_users'])
ai_datas: dict = json.loads(config["Dump"]['ai_datas'])


def save():
    config.set('Dump', 'ignore', json.dumps(ignore))
    config.set('Dump', 'images', json.dumps(images))
    config.set('Dump', 'current_chat', current_chat)
    config.set('Dump', 'auto_start', json.dumps(auto_start))
    config.set('Dump', 'users', json.dumps(users))
    config.set('Dump', 'groups', json.dumps(groups))
    config.set('Dump', 'birthdays', json.dumps(birthdays))
    config.set('Dump', 'active_goroda', json.dumps(active_goroda))
    config.set('Dump', 'current_letters', json.dumps(current_letters, ensure_ascii=False))
    config.set('Dump', 'wait_for_chat_id', json.dumps(wait_for_chat_id))
    config.set('Dump', 'chat_id_my', json.dumps(chat_id_my))
    config.set('Dump', 'chat_id_pen', json.dumps(chat_id_pen))
    config.set('Dump', 'chat_msg_my', json.dumps(chat_msg_my))
    config.set('Dump', 'chat_msg_pen', json.dumps(chat_msg_pen))
    config.set('Dump', 'current_users', json.dumps(current_users))
    config.set('Dump', 'ai_datas', json.dumps(ai_datas, ensure_ascii=False))
    with open('config.ini', 'w', encoding="utf-8") as file:
        config.write(file)


with open('cities.json', encoding="utf-8") as f:
    goroda = json.loads(f.read())


class ExceptionHandler(telebot.ExceptionHandler):
    def handle(self, exception):
        if "Bot token is not defined" in exception.args[0]:
            print("Неправильный токен бота")
            # noinspection PyProtectedMember
            os._exit(0)
        bot.send_message(admin_chat, "<b>ОШИБКА:</b>\n" + str(traceback.format_exc()), "HTML")


TOKEN = os.getenv("Kozlovskiy_token")
bot = telebot.TeleBot(TOKEN, exception_handler=ExceptionHandler())


def get_id(message):
    wait_for_chat_id.append(str(message.chat.id))
    bot.send_message(
        message.chat.id, "Теперь перешли мне любое сообщение из чата, "
                         "или поделись со мной контактом этого человека.\n /cancel - отмена")
    save()


def start_chat(chat_id, chat):
    try:
        if chat == chat_id:
            bot.send_message(chat_id, "<b>Нельзя писать самому себе через Козловского.</b>",
                             'HTML')
            return
        if chat_id in chat_id_my:
            bot.send_message(chat_id, "<b>Вы уже пишете кому-то через Козловского.\n"
                                      "Чтобы закончить, введите /cancel</b>", 'HTML')
            return
        chat_info = bot.get_chat(chat)
        markup = telebot.types.InlineKeyboardMarkup()
        if chat_info.photo is not None:
            markup.add(
                telebot.types.InlineKeyboardButton(
                    text="Посмотреть фото профиля",
                    callback_data="btn_photo_" + chat))
        if chat_info.pinned_message is not None:
            markup.add(
                telebot.types.InlineKeyboardButton(text="Посмотреть закреп",
                                                   callback_data=f"btn_pinned_{chat_info.pinned_message.chat.id}_"
                                                                 f"{chat_info.pinned_message.message_id}_"
                                                                 f"{chat_info.pinned_message.from_user.first_name}"))
        bot.send_message(chat_id, parse_chat(chat_info) +
                         "\n\n<b>/cancel - закончить переписку\n"
                         "/delete - удалить сообщение у собеседника</b>",
                         'HTML', reply_markup=markup)
        chat_id_my.append(chat_id)
        chat_id_pen.append(chat)
        current_users.append("")
        chat_msg_my.append([])
        chat_msg_pen.append([])
        save()
    except telebot.apihelper.ApiTelegramException:
        bot.send_message(chat_id, "Неправильный chat_id")


def get_city_letter(str_city, i=-1):
    if str_city[i] in goroda:
        return str_city[i]
    return str_city[i - 1]


def set_next_time(chat_id: str):
    auto_start[chat_id] = int(datetime.now(ZoneInfo("Europe/Moscow")).timestamp()) + random.randint(
        MIN_IGNORE_TIME, MAX_IGNORE_TIME)


def ai_talk(chat_id: str, msg_text, args, is_private=True, auto_answer=""):
    try:
        msgs = ai_datas[chat_id]
        if any(s in args for s in ends):
            ai_datas.pop(chat_id)
            bot.send_message(chat_id, "Пока")
            save()
            return
        if msg_text != "":
            bot.send_chat_action(chat_id, action="typing")
            ai_datas[chat_id].append(msg_text)
            if auto_answer == "":
                res = requests.post('https://api.aicloud.sbercloud.ru/public/v2/boltalka/predict',
                                    json={"instances": [{"contexts": [msgs]}]}).json()
                answer = str(res["responses"][2:-2]).replace("%bot_name", random.choice(["Даня", "Козловский"]))
            else:
                answer = auto_answer
            if is_private and chat_id in auto_start:
                set_next_time(chat_id)
            bot.send_message(chat_id, answer, disable_notification=auto_answer != "")
            ai_datas[chat_id].append(answer)
            ai_datas[chat_id] = msgs[-20:]
            save()
    except KeyError:
        if any(s in args for s in calls) or (is_private and any(s in args for s in calls_private)):
            ai_datas.setdefault(chat_id, [])
            ai_talk(chat_id, msg_text, args, is_private, auto_answer)
            save()


def photo_search(chat_id, search_photo):
    bot.send_chat_action(chat_id, action="typing")
    url_pic = "https://yandex.ru/images/search?rpt=imageview&url=" + bot.get_file_url(
        search_photo.file_id)
    soup = BeautifulSoup(requests.get(url_pic).text, 'lxml')
    results_vk = soup.find('div', class_='CbirSites-ItemInfo')
    if 'vk.com/id' in results_vk.find('a').get('href'):
        bot.send_message(chat_id, results_vk.find('div', class_='CbirSites-ItemDescription').get_text())
        return
    results = soup.find('section', 'CbirTags').find_all('a')
    bot.send_message(
        chat_id, results[0].find('span').get_text() + ", " + results[1].find('span').get_text())


def todict(obj):
    data = {}
    for key, value in obj.__dict__.items():
        try:
            data[key] = todict(value)
        except AttributeError:
            data[key] = value
    return data


def n(text: str, addition=''):
    """Если text - None, то вернуть пустую строку"""
    try:
        return "" if text is None else addition + text
    except telebot.apihelper.ApiTelegramException:
        return ""


def parse_chat(chat: telebot.types.Chat):
    text = "<b>Начат чат с:</b>\n\n"
    if chat.type == "private":
        text += '<b>Человек<a href="tg://user?id=' + str(chat.id) + '">: ' + chat.first_name + \
                n(chat.last_name, ' ') + '</a></b>' + n(chat.bio, '\n<b>Описание:</b> ') + n(chat.username, '\n@')
    elif chat.type == "channel":
        return str(todict(chat))
    else:
        text += "<b>Группа:</b> " + chat.title + n(chat.description, '\n<b>Описание:</b> ') + \
                n(chat.username, '\n@') + n(chat.invite_link, '\n<b>Ссылка:</b> ')
        try:
            text += n(str(bot.get_chat_member_count(chat.id)), '\n<b>Участников:</b> ')
            text += "\n<b>Админы:</b> "
            for m in bot.get_chat_administrators(chat.id):
                text += '\n\n<b><a href="tg://user?id=' + str(m.user.id) + '">' + m.user.first_name + \
                        '</a></b> <pre>' + str(m.user.id) + '</pre> ' + n(m.user.username, '\n@')

        except telebot.apihelper.ApiTelegramException:
            pass
    return text


def get_available(exist_images, results, is_groups, start_index=0):
    index = 0
    for g in groups if is_groups else users:
        index += 1
        current = bot.get_chat(g)
        if current.photo is None:
            thumb_url = None
        else:
            photo_id = current.photo.small_file_id
            file_name = photo_id + ".jpg"
            image_url = "static/" + file_name
            if is_local:
                if file_name not in exist_images:
                    requests.post(webserver.url + "upload/" + file_name, data=bot.download_file(
                        bot.get_file(photo_id).file_path))
            else:
                if not os.path.exists(image_url):
                    with open(image_url, 'wb') as new_photo:
                        new_photo.write(bot.download_file(bot.get_file(photo_id).file_path))
            thumb_url = webserver.url + image_url
        results.append(
            telebot.types.InlineQueryResultArticle(
                index + start_index,
                current.title if is_groups else current.first_name + n(current.last_name, " "),
                telebot.types.InputTextMessageContent("/chat " + g),
                description=(n(current.description) if is_groups else n(
                    current.bio)) + "\nНажмите, чтобы написать в этот чат",
                thumb_url=thumb_url))
    return index


def timer():
    while True:
        now = datetime.now(ZoneInfo("Europe/Moscow"))
        for key in birthdays:
            if MIN_BIRTHDAY_HOUR <= now.hour and now.day == birthdays[key][0] and now.month == birthdays[key][1]:
                if not birthdays[key][2]:
                    bot.send_message(admin_chat, "Я поздравил с ДР: " + key)
                    bot.send_video(key, success_vid, caption="<b>Поздравляю тебя с днём рождения!</b>🎉🎉🎉",
                                   parse_mode="HTML")
                    birthdays[key][2] = 1
            else:
                birthdays[key][2] = 0
            save()

        for key in auto_start:
            if key in chat_id_my or key in wait_for_chat_id:
                continue
            if auto_start[key] <= now.timestamp() and MIN_ALLOWED_HOUR <= now.hour <= MAX_ALLOWED_HOUR:
                bot.send_message(admin_chat, "Я написал: " + key)
                bot.send_message(key, "<i>/ignore - запретить Козловскому самому начинать переписку</i>", "HTML",
                                 disable_notification=True)
                ai_talk(key, "Привет", ["привет"], auto_answer=random.choice(starts))
        time.sleep(1000)


def new_group_cr(chat_id: str, title):
    if chat_id in groups:
        return
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton(text="Ignore", callback_data="btn_ignore_" + chat_id))
    bot.send_message(admin_chat, "<b>Новая группа: " + title + "  <pre>" +
                     chat_id + "</pre></b>", 'HTML', reply_markup=markup)
    groups.append(chat_id)
    save()


def new_private_cr(chat_id: str):
    if chat_id in users:
        return
    users.append(chat_id)
    bot.send_video(chat_id, success_vid, caption="<b>Чем я могу помочь?</b>🤔", parse_mode="HTML")
    set_next_time(chat_id)
    save()
