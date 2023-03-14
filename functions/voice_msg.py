import json
import re
import subprocess
import sys

import requests
import telebot
from telebot.types import Message

from helpers.bot import bot
from helpers.config import tts_key

re_emoji = re.compile(u"[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]+",
                      flags=re.UNICODE)


def decode_cmd_handler(msg: Message):
    file_id = get_voice_id(msg, True)
    if file_id is None:
        bot.send_message(msg.chat.id,
                         "<b>Ответьте на голосовое/видео сообщение командой /d, чтобы его расшифровать.</b>"
                         "\n<i>Если вы сделали всё правильно и видите это сообщение, "
                         "то перешлите сюда это голосовое</i>", 'HTML')
    else:
        stt(file_id, msg.reply_to_message)


def get_voice_id(msg: telebot.types.Message, reply: bool):
    if reply:
        if msg.reply_to_message is None:
            return None
        msg1 = msg.reply_to_message
    else:
        msg1 = msg
    file_id = None
    if msg1.content_type == "voice":
        file_id = msg1.voice.file_id
    elif msg1.content_type == "audio":
        file_id = msg1.audio.file_id
    elif msg1.content_type == "video_note":
        file_id = msg1.video_note.file_id
    elif msg1.content_type == "video":
        file_id = msg1.video.file_id
    return file_id


def stt(file_id: str, reply_to_message=None):
    stats = reply_to_message is not None
    progress_id = -1
    if stats:
        progress_id = bot.reply_to(reply_to_message, "Расшифровка...").message_id

    cmd = [f'{sys.path[0]}\\ffmpeg.exe' if sys.platform == "win32" else f'{sys.path[0]}/ffmpeg', '-n', '-i',
           bot.get_file_url(file_id), '-ac', '1', '-ar', '48000', '-acodec', 'flac', '-f', 'flac', 'pipe:']
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    try:
        raw = proc.stdout.read()
        if stats:
            bot.edit_message_text("Расшифровка... 50%", reply_to_message.chat.id, progress_id)

        url = "http://www.google.com/speech-api/v2/recognize?client=chromium&lang=ru-RU&" \
              "key=AIzaSyBOti4mM-6x9WDnZIjIeyEU21OpBXqWBgw&pFilter=0"
        response_text = requests.post(url, data=raw, headers={"Content-Type": f"audio/x-flac; rate=48000;"}).text
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
