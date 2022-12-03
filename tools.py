#!/usr/bin/python3
import configparser
import json
import os
import random
import subprocess
import sys
import time
import traceback
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, db, storage
import requests

if sys.version_info < (3, 9):
    # noinspection PyUnresolvedReferences,PyPackageRequirements
    from backports.zoneinfo import ZoneInfo
else:
    from zoneinfo import ZoneInfo
import telebot
from bs4 import BeautifulSoup

content_types = [
    "text", "audio", "document", "photo", "sticker", "video", "video_note",
    "voice", "location", "contact", "group_chat_created", "chat_member",
    "supergroup_chat_created", "channel_chat_created", "migrate_to_chat_id", "poll"]
config = configparser.ConfigParser()
config.read("config.ini", encoding="utf8")  # читаем конфиг
MIN_BIRTHDAY_HOUR = config.getint("Settings", "MIN_BIRTHDAY_HOUR")
admin_chat = json.loads(config["Settings"]['admin_chat'])
success_vid = json.loads(config["Settings"]['success_vid'])
calls = json.loads(config["Settings"]['calls'])
calls_private = json.loads(config["Settings"]['calls_private'])
ends = json.loads(config["Settings"]['ends'])
searches = json.loads(config["Settings"]['searches'])
samplerate = 16000
samplerate_tts = 48000

with open('db.json', encoding="utf-8") as bd_file:
    bd = json.load(bd_file)

cred = credentials.Certificate("firebase-key.json")
firebase_admin.initialize_app(cred, {'databaseURL': os.getenv("db_url"),
                                     'storageBucket': os.getenv("storage_url")})
ref = db.reference()
bucket = storage.bucket()

ignore: list = bd['ignore']
images: dict = bd['images']
current_chat = bd['current_chat']
users: dict[str, dict] = bd['users']
active_goroda: list = bd['active_goroda']
current_letters = bd['current_letters']
chat_id_my = bd['chat_id_my']
chat_id_pen: list = bd['chat_id_pen']
chat_msg_my = bd['chat_msg_my']
chat_msg_pen = bd['chat_msg_pen']
current_users = bd['current_users']


def save():
    bd['ignore'] = ignore
    bd['images'] = images
    bd['current_chat'] = current_chat
    bd['users'] = users
    bd['active_goroda'] = active_goroda
    bd['current_letters'] = current_letters
    bd['chat_id_my'] = chat_id_my
    bd['chat_id_pen'] = chat_id_pen
    bd['chat_msg_my'] = chat_msg_my
    bd['chat_msg_pen'] = chat_msg_pen
    bd['current_users'] = current_users
    to_save = json.dumps(bd, ensure_ascii=False)
    with open('db.json', 'w', encoding='utf-8') as db_file1:
        db_file1.write(to_save)

    ref.set(bd)


with open('cities.json', encoding="utf-8") as f:
    goroda = json.loads(f.read())


class ExceptionHandler(telebot.ExceptionHandler):
    def handle(self, exception):
        bot.send_message(admin_chat, "ОШИБКА:\n" + traceback.format_exc())


TOKEN = os.getenv("Kozlovskiy_token")
bot = telebot.TeleBot(TOKEN)  # TODO exception_handler=ExceptionHandler()


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
        bot.send_message(chat_id, "<b>Чат не найден</b>", 'HTML')


def get_city_letter(str_city, i=-1):
    if str_city[i] in goroda:
        return str_city[i]
    return str_city[i - 1]


def ai_talk(msg_text, chat_id: str, is_private=True, args=None, start='', append=False, send=False, msg_voice=None):
    talk = users[chat_id].get("talk")
    if talk is None:
        if start:
            users[chat_id]["talk"] = [msg_text, start]
            if send:
                bot.send_message(chat_id, start)
            save()
            return
        elif any(s in args for s in calls) or (is_private and any(s in args for s in calls_private)):
            users[chat_id]["talk"] = []
            talk = users[chat_id].get("talk")
            save()
        else:
            return
    elif not start and any(s in args for s in ends):
        users[chat_id].pop("talk")
        bot.send_message(chat_id, "Пока👋")
        save()
        return
    if append:
        users[chat_id]["talk"] += [msg_text, start]
        save()
        return
    voice_id = None if start else get_voice_id(msg_voice)
    is_voice = voice_id is not None
    if is_voice:
        bot.send_chat_action(chat_id, action="record_voice")
        msg_text = stt(voice_id) + ("\n" + msg_text if msg_text != "" else "")
    else:
        bot.send_chat_action(chat_id, action="typing")
    if msg_text:
        talk.append(msg_text)
        res = requests.post('https://api.aicloud.sbercloud.ru/public/v2/boltalka/predict',
                            json={"instances": [{"contexts": [talk]}]}).json()
        answer = str(res["responses"][2:-2]).replace("%bot_name", random.choice(["Даня", "Козловский"]))
        if is_voice:
            bot.send_voice(chat_id, tts(answer))
        else:
            bot.send_message(chat_id, answer)
        talk.append(answer)
        save()


def photo_search(chat_id, msg_id, search_photo):
    bot.send_chat_action(chat_id, action="typing")
    url_pic = "https://yandex.ru/images/search?rpt=imageview&url=" + bot.get_file_url(search_photo.file_id)
    soup = BeautifulSoup(requests.get(url_pic).text, 'lxml')
    results_vk = soup.find('div', class_='CbirSites-ItemInfo')
    if 'vk.com/id' in results_vk.find('a').get('href'):
        bot.send_message(chat_id, results_vk.find('div', class_='CbirSites-ItemDescription').get_text(),
                         reply_to_message_id=msg_id)
        return
    results = soup.find('section', 'CbirTags').find_all('a')
    bot.send_message(chat_id, results[0].find('span').get_text() + ", " + results[1].find('span').get_text(),
                     reply_to_message_id=msg_id)


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
    text = ""
    if chat.type == "private":
        text += '<b>Начат чат с<a href="tg://user?id=' + str(chat.id) + '">: ' + chat.first_name + \
                n(chat.last_name, ' ') + '</a></b>' + n(chat.bio, '\n<b>Описание:</b> ') + n(chat.username, '\n@')
    elif chat.type == "channel":
        return str(todict(chat))
    else:
        text += "<b>Начат чат с группой:</b> " + chat.title + n(chat.description, '\n<b>Описание:</b> ') + \
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


def get_exist_images():
    exist_images = {}
    for b in bucket.list_blobs():
        exist_images[b.name] = b.public_url
    return exist_images


def update_user_info(user: telebot.types.Chat, exist_images):
    chat = str(user.id)
    users[chat]['private'] = user.type == "private"
    users[chat]['name'] = user.title if not user.type == "private" else user.first_name + n(user.last_name, " ")
    users[chat]['desc'] = n(user.bio) if user.type == "private" else n(user.description)
    if user.photo is not None:
        file_name = user.photo.small_file_id + ".jpg"
        photo_url = exist_images.get(file_name)
        if photo_url is None:
            blob = bucket.blob(file_name)
            blob.upload_from_string(bot.download_file(bot.get_file(user.photo.small_file_id).file_path),
                                    content_type='image/jpg')
            blob.make_public()
            users[chat]['photo_url'] = blob.public_url
        else:
            users[chat]['photo_url'] = photo_url


def timer():
    while True:
        now = datetime.now(ZoneInfo("Europe/Moscow"))
        exist_images = get_exist_images()
        for u in users:
            update_user_info(bot.get_chat(u), exist_images)

            birthday: str = users[u].get("birthday")
            if birthday is None:
                continue
            day, month = birthday.split("/")
            if MIN_BIRTHDAY_HOUR <= now.hour and now.day == int(day) and now.month == int(month):
                if users[u].get("congratulated", 0):
                    continue
                bot.send_video(u, success_vid, caption="<b>Поздравляю тебя с днём рождения!</b>🎉🎉🎉",
                               parse_mode="HTML")
                bot.send_message(admin_chat, "Я поздравил с ДР: " + u)
                users[u]["congratulated"] = 1
                ai_talk("У меня сегодня день рождения!", u, start="Поздравляю тебя с днём рождения!🎉🎉🎉", append=True)
            else:
                users[u].pop("congratulated", 0)
        save()
        time.sleep(3000)


def new_group_cr(chat: telebot.types.Chat):
    chat_id = str(chat.id)
    if users.get(chat_id) is not None:
        return
    users[chat_id] = {}
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton(text="Ignore", callback_data="btn_ignore_" + chat_id))
    bot.send_message(admin_chat, "<b>Новая группа: " + chat.title + "  <pre>" +
                     chat_id + "</pre></b>", 'HTML', reply_markup=markup)
    update_user_info(bot.get_chat(chat.id), get_exist_images())
    save()


def new_private_cr(chat: telebot.types.Chat):
    chat_id = str(chat.id)
    if users.get(chat_id) is not None:
        return False
    users[chat_id] = {}
    bot.send_video(chat_id, success_vid, caption="<b>Чем я могу помочь?</b>🤔", parse_mode="HTML")
    ai_talk("/start", str(chat.id), start="Чем я могу помочь?🤔")
    update_user_info(bot.get_chat(chat.id), get_exist_images())
    save()
    return True


def get_voice_id(msg: telebot.types.Message):
    file_id = None
    if msg.content_type == "voice":
        file_id = msg.voice.file_id
    elif msg.content_type == "audio":
        file_id = msg.audio.file_id
    elif msg.content_type == "video_note":
        file_id = msg.video_note.file_id
    elif msg.content_type == "video":
        file_id = msg.video.file_id
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


def stt(file_id: str, reply_to_message=None):
    global rec
    stats = reply_to_message is not None
    progress_id = -1
    if stats:
        progress_id = bot.reply_to(reply_to_message, "Расшифровка...").message_id

    command = [
        f'{sys.path[0]}\\ffmpeg.exe' if sys.platform == "win32" else 'ffmpeg',
        '-n', '-i', bot.get_file_url(file_id),
        '-ac', '1', '-ar', str(samplerate), '-acodec', 'pcm_s16le', '-f', 's16le', 'pipe:'
    ]
    proc = subprocess.Popen(command, bufsize=samplerate * 8, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    result = ''
    while rec is None:
        time.sleep(0.5)
    while proc.poll() is None:
        audio = proc.stdout.read(samplerate * 8)
        if rec.AcceptWaveform(audio):
            result += json.loads(rec.Result())['text']

    result += json.loads(rec.FinalResult())['text']
    if result == '':
        result = "Тут ничего нет🤔" if stats else "Скажи что-нибудь"
    if stats:
        bot.edit_message_text(result, reply_to_message.chat.id, progress_id)

    return result


def tts(text: str):
    # noinspection PyUnresolvedReferences
    audio = tts_model.apply_tts(text=text, speaker='eugene')
    command = [
        f'{sys.path[0]}\\ffmpeg.exe' if sys.platform == "win32" else f'ffmpeg',
        '-n', '-f', 's16le', '-ac', '1',
        '-ar', str(samplerate_tts), '-i', 'pipe:',
        '-ac', '1', '-ar', str(samplerate_tts),
        '-acodec', 'libopus', '-f', 'opus', 'pipe:']
    proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    out = proc.communicate(input=(audio * 32767).numpy().astype('int16').tobytes())[0]

    return out
