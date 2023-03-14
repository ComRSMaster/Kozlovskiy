import random

import requests

from functions.voice_msg import get_voice_id, stt, tts
from helpers.bot import bot
from helpers.config import calls, ends, calls_private
from helpers.storage import users, save


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
    voice_id = None if start else get_voice_id(msg_voice, False)
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
    talk = talk[-40:]
    save()
