#!/usr/bin/python3
import logging
import time
import configparser
import json
import os
import random
import re
import subprocess
import sys
from datetime import datetime
from io import StringIO

import requests

if sys.version_info < (3, 9):
    # noinspection PyUnresolvedReferences,PyPackageRequirements
    from backports.zoneinfo import ZoneInfo
else:
    from zoneinfo import ZoneInfo
import telebot
from bs4 import BeautifulSoup

content_types = ["text", "audio", "document", "photo", "sticker", "video", "video_note", "voice",
                 "location", "contact", "poll", "chat_member"]
config = configparser.ConfigParser()
config.read("config.ini", encoding="utf8")  # читаем конфиг
MIN_BIRTHDAY_HOUR = config.getint("Settings", "MIN_BIRTHDAY_HOUR")
admin_chat = json.loads(config["Settings"]['admin_chat'])
success_vid = json.loads(config["Settings"]['success_vid'])
calls = json.loads(config["Settings"]['calls'])
calls_private = json.loads(config["Settings"]['calls_private'])
ends = json.loads(config["Settings"]['ends'])
searches = json.loads(config["Settings"]['searches'])

with open('db.json', encoding="utf-8") as bd_file:
    bd = json.load(bd_file)

tts_key = os.getenv("tts_key")
web_url = os.getenv("web_url")
fb_url = os.getenv("fb_url")

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
help_text = \
    "/start - Начать разговор с ИИ. <i>Также можно просто написать \"<code>Привет</code>\", \"<code>Даня</code>\" " \
    "или \"<code>Козловский</code>\".</i>\nЧтобы закончить, напишите \"<code>Пока</code>\", \"<code>Стоп</code>\" " \
    "или \"<code>Хватит</code>\"\n" \
    "/help - Помощь по функционалу бота <i>(это сообщение)</i>\n" \
    "/d - Расшифровка голосовых/видео сообщений: для этого нужно <b>ответить</b> на такое сообщение этой командой\n" \
    "/chat - Анонимная переписка от имени Козловского:\n1. Введите эту команду\n2. Нажмите кнопку \"<i>Выбрать чат" \
    "</i>\"\n3. Выберите нужный вам чат.\nПосле этого <b>все сообщения, которые вы отправите, будут доставлены в " \
    "чат, который вы выбрали</b>.\nЧтобы <b>закончить</b> переписку, введите /cancel.\nЧтобы <b>удалить</b> " \
    "сообщение у собеседника, <b>ответьте</b> на своё сообщение командой /delete\n" \
    "/id - Узнать <i>chat_id</i> человека для команды /chat\n" \
    "/rnd - Случайное число <i>(по умолчанию от 1 до 6)</i>:\n<code>/rnd a</code> - случайное число от 1 до a\n" \
    "<code>/rnd a b</code> - случайное число от a до b\n<i>Например:</i> <code>/rnd 5 10</code> - случайное число " \
    "от 5 до 10\n" \
    "/books - Открыть базу конспектов и готовых билетов\n" \
    "/cancel - Отмена выполнения текущей команды\n" \
    "<b>Также бот умеет:</b>\n• Поздравлять с днём рождения\n• Выбирать случайный ответ в голосованиях\n" \
    "• Искать по фото (для этого ответьте на фото словами \"<code>Что " \
    "это</code>\" или \"<code>Кто это</code>\")\n• Играть в города (для этого напишите \"<code>В города</code>\", " \
    "выберите сложность <i>(<b>Лёгкий</b> - 500 городов, <b>Хардкор</b> - 10000 городов)</i>, и вводите город " \
    "первым), чтобы закончить, напишите \"<code>Стоп</code>\" или \"<code>Хватит</code>\""
book_orig_text = "<b>📕Конспекты и готовые билеты📙</b>\n\n" \
                 "Выбери нужный класс, " \
                 "чтобы <i>найти</i> или <i>выложить</i> нужный конспект"
re_emoji = re.compile(u"[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]+",
                      flags=re.UNICODE)


def save():
    bd['ignore'] = ignore
    bd['images'] = images
    bd['current_chat'] = current_chat
    bd['users'] = users
    bd['chat_id_my'] = chat_id_my
    bd['chat_id_pen'] = chat_id_pen
    bd['chat_msg_my'] = chat_msg_my
    bd['chat_msg_pen'] = chat_msg_pen
    bd['current_users'] = current_users
    to_save = json.dumps(bd, ensure_ascii=False)
    with open('db.json', 'w', encoding='utf-8') as db_file1:
        db_file1.write(to_save)
    requests.put(f'{fb_url}.json', data=to_save.encode("utf-8"),
                 headers={"content-type": "application/json; charset=UTF-8"})


with open('cities_easy.json', encoding="utf-8") as f:
    cities_easy = json.loads(f.read())

with open('cities_hard.json', encoding="utf-8") as f:
    cities_hard = json.loads(f.read())

log_stream = StringIO()
logging.basicConfig(stream=log_stream, level=logging.WARNING)


class ExceptionHandler(telebot.ExceptionHandler):
    def handle(self, exception):
        telebot.logger.error(exception, exc_info=True)
        bot.send_message(admin_chat, "ОШИБКА:\n" + log_stream.getvalue())
        log_stream.truncate(0)


TOKEN = os.getenv("Kozlovskiy_token")
bot = telebot.TeleBot(TOKEN, exception_handler=ExceptionHandler())


def start_chat(chat_id, chat):
    try:
        if chat == chat_id:
            bot.send_message(chat_id, "<b>Нельзя писать самому себе через Козловского.</b>", 'HTML')
            return
        if chat_id in chat_id_my:
            bot.send_message(chat_id, "<b>Вы уже пишете кому-то через Козловского.\n"
                                      "Чтобы закончить, введите /cancel</b>", 'HTML')
            return
        chat_info = bot.get_chat(chat)
        elem = {}
        if chat_info.photo is not None:
            elem["Посмотреть фото профиля"] = {'callback_data': "btn_photo_" + chat}
        p_msg = chat_info.pinned_message
        if p_msg is not None:
            elem["Посмотреть закреп"] = {
                'callback_data': f"btn_pinned_{p_msg.chat.id}_{p_msg.message_id}_{p_msg.from_user.first_name}"}
        bot.send_message(chat_id, parse_chat(chat_info) +
                         "\n\n<b>/cancel - закончить переписку\n/delete - удалить сообщение у собеседника</b>", 'HTML',
                         reply_markup=telebot.util.quick_markup(elem, row_width=3))
        chat_id_my.append(chat_id)
        chat_id_pen.append(chat)
        current_users.append("")
        chat_msg_my.append([])
        chat_msg_pen.append([])
        save()
    except telebot.apihelper.ApiTelegramException:
        bot.send_message(chat_id, "<b>Чат не найден</b>", 'HTML')


def get_city_letter(str_city, i=-1):
    if str_city[i] in cities_easy:
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
    elif msg_text:
        bot.send_chat_action(chat_id, action="typing")
    else:
        return
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
    url_pic = f"https://yandex.ru/images/search?rpt=imageview&url={bot.get_file_url(search_photo.file_id)}"
    soup = BeautifulSoup(requests.get(url_pic).text, 'lxml')
    results_vk = soup.find('div', class_='CbirSites-ItemInfo')
    if 'vk.com/id' in results_vk.find('a').get('href'):
        bot.send_message(chat_id, results_vk.find('div', class_='CbirSites-ItemDescription').get_text(),
                         reply_to_message_id=msg_id)
        return
    results = soup.find('section', 'CbirTags').find_all('a')
    bot.send_message(chat_id, '\n'.join('• ' + res.find('span').get_text().capitalize() for res in results),
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


def update_user_info(chat: telebot.types.Chat):
    chat_id = str(chat.id)
    users[chat_id]['private'] = chat.type == "private"
    users[chat_id]['name'] = chat.title if not chat.type == "private" else chat.first_name + n(chat.last_name, " ")
    users[chat_id]['desc'] = n(chat.bio) if chat.type == "private" else n(chat.description)
    if chat.photo is None:
        users[chat_id]['photo_id'] = None
    else:
        file_name = chat.photo.small_file_unique_id + ".jpg"
        if not os.path.isfile(
                f'website/p/{file_name}') or chat.photo.small_file_unique_id != users[chat_id].get('photo_id'):
            with open(f'website/p/{file_name}', 'wb') as file:
                file.write(bot.download_file(bot.get_file(chat.photo.small_file_id).file_path))
        users[chat_id]['photo_id'] = chat.photo.small_file_unique_id


def timer():
    while True:
        now = datetime.now(ZoneInfo("Europe/Moscow"))
        for u in users:
            update_user_info(bot.get_chat(u))
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
    update_user_info(bot.get_chat(chat.id))
    save()


def new_private_cr(chat: telebot.types.Chat):
    chat_id = str(chat.id)
    users[chat_id] = {}
    bot.send_message(chat_id, help_text, 'HTML')
    bot.send_video(chat_id, success_vid, caption="<b>Чем я могу помочь?</b>🤔", parse_mode="HTML")
    ai_talk("/start", str(chat.id), start="Чем я могу помочь?🤔")
    update_user_info(bot.get_chat(chat.id))
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
    stats = reply_to_message is not None
    progress_id = -1
    if stats:
        progress_id = bot.reply_to(reply_to_message, "Расшифровка...").message_id

    cmd = [f'{sys.path[0]}\\ffmpeg.exe' if sys.platform == "win32" else f'{sys.path[0]}/ffmpeg', '-n', '-i',
           bot.get_file_url(file_id), '-ac', '1', '-ar', '48000', '-acodec', 'pcm_s16le', '-f', 's16le', 'pipe:']
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    try:
        raw = proc.stdout.read()
        if stats:
            bot.edit_message_text("Расшифровка... 50%", reply_to_message.chat.id, progress_id)

        url = "http://www.google.com/speech-api/v2/recognize?client=chromium&lang=ru-RU&" \
              "key=AIzaSyBOti4mM-6x9WDnZIjIeyEU21OpBXqWBgw&pFilter=0"
        response_text = requests.post(url, data=raw, headers={"Content-Type": "audio/l16; rate=48000;"}).text
        actual_result = []
        for line in response_text.split("\n"):
            if not line:
                continue
            current_result = json.loads(line)["result"]
            if len(current_result) != 0:
                actual_result = current_result[0]
                break
        if not isinstance(actual_result, dict) or len(actual_result.get("alternative", [])) == 0:
            result = ''
        else:
            best_hypothesis = max(actual_result["alternative"], key=lambda alternative: alternative[
                "confidence"]) if "confidence" in actual_result["alternative"] else actual_result["alternative"][0]
            result = '' if "transcript" not in best_hypothesis else best_hypothesis["transcript"]
    except requests.exceptions.RequestException as e:
        result = f"❌Возникла ошибка: {e}" if stats else "Скажи что-нибудь"
    if not result:
        result = "Тут ничего нет🤔" if stats else "Скажи что-нибудь"

    if stats:
        bot.edit_message_text(result, reply_to_message.chat.id, progress_id)

    return result


def tts(text: str):
    cmd = [f'{sys.path[0]}\\ffmpeg.exe' if sys.platform == "win32" else f'{sys.path[0]}/ffmpeg', '-n', '-i',
           f"https://api.voicerss.org/?key={tts_key}&hl=ru-RU&v=Peter&r=2&f=24khz_16bit_mono&"
           f"src={re_emoji.sub(r'', text)}", '-ac', '1', '-ar', '24000', '-acodec', 'libopus', '-f', 'opus', 'pipe:']
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    return proc.communicate()[0]
