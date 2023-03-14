import time

import requests
from telebot.apihelper import ApiTelegramException
from telebot.types import Message, ForceReply
from telebot.util import extract_arguments

from helpers.bot import bot
from helpers.config import replicate_key
from helpers.storage import save, users


def upscale_cmd_handler(msg: Message):
    file_id = None
    if msg.reply_to_message is not None:
        if msg.reply_to_message.content_type == "photo":
            file_id = msg.reply_to_message.photo[-1].file_id
        elif msg.reply_to_message.content_type == "document":
            file_id = msg.reply_to_message.document.file_id
    try:
        scale = float(extract_arguments(msg.text))
    except ValueError:
        scale = 2
    if file_id is None:
        bot.send_message(msg.chat.id,
                         "<b>✨Улучшение качества фото через нейросеть✨</b>\n\n"
                         "Чтобы улучшить фото, отправь его прямо сейчас <i>(желательно без сжатия)\n</i>"
                         "Также можно ответить командой <code>/up N</code> на уже отправленное фото, "
                         "где N - масштаб улучшения, <i>(по умолчанию 2)</i>\n"
                         f"Текущий масштаб: <b>{scale}</b>", 'HTML',
                         reply_markup=ForceReply(input_field_placeholder="Отправь фото"))
        users[str(msg.chat.id)]['s'] = 'up_photo'
        users[str(msg.chat.id)]['sd'] = scale
        save()
    else:
        gfpgan(msg.chat.id, file_id, scale)


def wait_photo_state(msg: Message):
    if msg.content_type == "photo":
        file_id = msg.photo[-1].file_id
    elif msg.content_type == "document":
        file_id = msg.document.file_id
    else:
        bot.send_message(msg.chat.id,
                         "Можно улучшать только обычные фото или фото без сжатия.\n"
                         "<b>Отправь фото ещё раз.</b>\n\n"
                         "<i>Для отмены введи /cancel</i>", 'HTML',
                         reply_markup=ForceReply(input_field_placeholder="Отправь фото"))
        return
    gfpgan(msg.chat.id, file_id, users[str(msg.chat.id)]['sd'])
    save()


def gfpgan(chat_id, file_id, scale):
    bot.send_chat_action(chat_id, "upload_document")
    post = requests.post(
        "https://api.replicate.com/v1/predictions",
        json={"version": "9283608cc6b7be6b65a8e44983db012355fde4132009bf99d976b2f0896856a3",
              "input": {"img": bot.get_file_url(file_id), "scale": scale}},
        headers={"Authorization": f"Token {replicate_key}", "Content-Type": "application/json"})
    rec_json = post.json()

    while rec_json['status'] not in ["succeeded", "failed", "canceled"]:
        time.sleep(0.5)
        get = requests.get(
            rec_json['urls']['get'],
            headers={"Authorization": f"Token {replicate_key}", "Content-Type": "application/json"})
        rec_json = get.json()
    if rec_json['status'] == "succeeded":
        try:
            bot.send_document(chat_id, rec_json['output'])
        except ApiTelegramException:
            bot.send_message(chat_id, rec_json['output'])
        users[str(chat_id)]['s'] = users[str(chat_id)]['sd'] = ''
        save()
    elif rec_json['status'] == "canceled":
        bot.send_message(chat_id, "<b>🛑 Команда отменена!</b>", 'HTML')
    else:
        if rec_json['error'].startswith("local variable"):
            bot.send_message(chat_id, "<b>❌ Тип файла не поддерживается...</b>", 'HTML')
        else:
            bot.send_message(chat_id, f"<b>❌ Неизвестная ошибка...</b>", 'HTML')
