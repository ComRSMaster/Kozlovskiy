import configparser
import json
import os
import random
import subprocess
import sys
import time
import traceback
import wave
from datetime import datetime

import requests
import vosk

if sys.version_info < (3, 9):
    # noinspection PyUnresolvedReferences,PyPackageRequirements
    from backports.zoneinfo import ZoneInfo
else:
    from zoneinfo import ZoneInfo

from importlib import util

import telebot

from bs4 import BeautifulSoup

is_local = util.find_spec("replit") is None
del util

content_types = [
    "text", "audio", "document", "photo", "sticker", "video", "video_note",
    "voice", "location", "contact", "group_chat_created", "chat_member",
    "supergroup_chat_created", "channel_chat_created", "migrate_to_chat_id", "poll"]
config = configparser.ConfigParser()
config.read("config.ini", encoding="utf8")  # читаем конфиг
MIN_BIRTHDAY_HOUR = config.getint("Settings", "MIN_BIRTHDAY_HOUR")
admin_chat = json.loads(config["Settings"]['admin_chat'])
success_vid = json.loads(config["Settings"]['success_vid'])
starts = json.loads(config["Settings"]['starts'])
calls = json.loads(config["Settings"]['calls'])
calls_private = json.loads(config["Settings"]['calls_private'])
ends = json.loads(config["Settings"]['ends'])
searches = json.loads(config["Settings"]['searches'])
randoms = json.loads(config["Settings"]['randoms'])
samplerate = 48000

with open('db.json', encoding="utf-8") as db_file:
    db = json.load(db_file)

ignore: list = db['ignore']
images: dict = db['images']
current_chat = db['current_chat']
users: dict = db['users']
birthdays: dict = db['birthdays']
active_goroda: list = db['active_goroda']
current_letters = db['current_letters']
chat_id_my = db['chat_id_my']
chat_id_pen: list = db['chat_id_pen']
chat_msg_my = db['chat_msg_my']
chat_msg_pen = db['chat_msg_pen']
current_users = db['current_users']
ai_datas: dict = db['ai_datas']

rec = None


def load_ai():
    global rec
    rec = vosk.KaldiRecognizer(vosk.Model("model_small"), samplerate)
    print("ai loaded")


def save():
    db['ignore'] = ignore
    db['images'] = images
    db['current_chat'] = current_chat
    db['users'] = users
    db['birthdays'] = birthdays
    db['active_goroda'] = active_goroda
    db['current_letters'] = current_letters
    db['chat_id_my'] = chat_id_my
    db['chat_id_pen'] = chat_id_pen
    db['chat_msg_my'] = chat_msg_my
    db['chat_msg_pen'] = chat_msg_pen
    db['current_users'] = current_users
    db['ai_datas'] = ai_datas
    with open('db.json', 'w', encoding='utf-8') as db_file1:
        json.dump(db, db_file1, ensure_ascii=False)


with open('cities.json', encoding="utf-8") as f:
    goroda = json.loads(f.read())


class ExceptionHandler(telebot.ExceptionHandler):
    def handle(self, exception):
        if "Bot token is not defined" in exception.args[0]:
            print("Неправильный токен бота")
            # noinspection PyProtectedMember
            os._exit(0)
        bot.send_message(admin_chat, "ОШИБКА:\n" + str(traceback.format_exc()))


TOKEN = os.getenv("Kozlovskiy_token")
bot = telebot.TeleBot(TOKEN, exception_handler=ExceptionHandler())


def get_id(message):
    users[str(message.chat.id)]["getting_id"] = 1
    bot.send_message(message.chat.id, "Теперь перешли мне любое сообщение из чата, "
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


def ai_talk(chat_id: str, msg_text, voice_id, args, is_private=True):
    if chat_id in ai_datas:
        if any(s in args for s in ends):
            ai_datas.pop(chat_id)
            bot.send_message(chat_id, "Пока")
            save()
            return
        is_voice = voice_id is not None
        if is_voice:
            bot.send_chat_action(chat_id, action="record_voice")
            msg_text = stt(voice_id) + ("\n" + msg_text if msg_text != "" else "")
        else:
            bot.send_chat_action(chat_id, action="typing")
        if msg_text != "":
            ai_datas[chat_id].append(msg_text)
            res = requests.post('https://api.aicloud.sbercloud.ru/public/v2/boltalka/predict',
                                json={"instances": [{"contexts": [ai_datas[chat_id]]}]}).json()
            answer = str(res["responses"][2:-2]).replace("%bot_name", random.choice(["Даня", "Козловский"]))

            bot.send_message(chat_id, answer)
            ai_datas[chat_id].append(answer)
            ai_datas[chat_id] = ai_datas[chat_id][-30:]
            save()
    elif any(s in args for s in calls) or (is_private and any(s in args for s in calls_private)):
        ai_datas.setdefault(chat_id, [])
        ai_talk(chat_id, msg_text, voice_id, args, is_private)
        save()


def photo_search(chat_id, search_photo):
    bot.send_chat_action(chat_id, action="typing")
    url_pic = "https://yandex.ru/images/search?rpt=imageview&url=" + bot.get_file_url(search_photo.file_id)
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
        time.sleep(1000)


def new_group_cr(chat_id: str, title):
    if users.get(chat_id) is not None:
        return
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton(text="Ignore", callback_data="btn_ignore_" + chat_id))
    bot.send_message(admin_chat, "<b>Новая группа: " + title + "  <pre>" +
                     chat_id + "</pre></b>", 'HTML', reply_markup=markup)
    users[chat_id] = {}
    save()


def new_private_cr(chat_id: str):
    if users.get(chat_id) is not None:
        return
    users[chat_id] = {}
    bot.send_video(chat_id, success_vid, caption="<b>Чем я могу помочь?</b>🤔", parse_mode="HTML")
    save()


def get_voice_id(msg: telebot.types.Message):
    file_id = None
    if msg.content_type == "voice":
        file_id = msg.voice.file_id
    elif msg.content_type == "audio":
        file_id = msg.audio.file_id
    elif msg.content_type == "video_note":
        file_id = msg.video_note.file_id
    elif msg.content_type == "video":
        file_id = msg.reply_to_message.video.file_id
    elif msg.reply_to_message is not None:
        if msg.reply_to_message.content_type == "voice":
            file_id = msg.reply_to_message.voice.file_id
        elif msg.reply_to_message.content_type == "audio":
            file_id = msg.reply_to_message.audio.file_id
        elif msg.reply_to_message.content_type == "video_note":
            file_id = msg.reply_to_message.video_note.file_id
        elif msg.reply_to_message.content_type == "video":
            file_id = msg.reply_to_message.video.file_id
    return file_id


def stt(file_id, reply_to_message=None):
    global rec
    stats = reply_to_message is not None
    progress_id = -1
    if stats:
        progress_id = bot.reply_to(reply_to_message, "Расшифровка: 0%").message_id

    path = "cache/" + file_id
    if not os.path.exists(path + ".wav"):
        try:
            with open(path + ".ogg", "xb") as n_f:
                n_f.write(bot.download_file(bot.get_file(file_id).file_path))
        except FileExistsError:
            pass
        command = [
            f'{sys.path[0]}\\ffmpeg.exe' if sys.platform == "win32" else 'ffmpeg',
            '-n', '-i', path + ".ogg",
            '-acodec', 'pcm_s16le',
            '-ac', '1',
            '-ar', str(samplerate), path + ".wav"
        ]
        subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.remove(path + ".ogg")

    if stats:
        bot.edit_message_text("Расшифровка: 50%", reply_to_message.chat.id, progress_id)
    wf = wave.open(path + ".wav", "rb")
    result = ''
    while rec is None:
        time.sleep(0.5)
    while True:
        data = wf.readframes(samplerate)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            result += json.loads(rec.Result())['text']

    res = json.loads(rec.FinalResult())
    result += res['text']
    if result == '':
        result = "Тут ничего нет🤔" if stats else "Скажи что-нибудь"
    if stats:
        bot.edit_message_text(result, reply_to_message.chat.id, progress_id)

    return result

