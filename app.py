#!/usr/bin/python3
import os
import random
import re
import sys
from io import StringIO
from threading import Thread

from telebot.types import CallbackQuery, Message, ReplyKeyboardRemove
from telebot.util import quick_markup

from functions.casino import casino_cmd_handler, casino_handler, casino_balance_handler
from functions.weather import weather_cmd_handler, change_city_button, search_city, update_weather_button
from helpers import storage
from functions.ai_talk import ai_talk
from functions.ai_upscale import upscale_cmd_handler, wait_photo_state
from functions.books_base import done_cmd_handler, grade_inline_section, subject_inline_section, book_inline_section, \
    book_name_upload_state, book_upload_state, wait_user_upload_state, book_upload_button
from functions.chat_cmd import start_chat, delete_cmd_handler, end_chat, transfer_to_other, transfer_to_me, \
    edit_msg_handler, chat_cmd_handler, inline_query_photo, profile_photo_button, pinned_msg_button
from functions.cities_game import city_game_handler, inline_btn_complex_change
from functions.photo_desc import photo_search
from functions.voice_msg import decode_cmd_handler
from helpers.bot import start_bot, bot
from helpers.config import admin_chat, searches
from helpers.long_texts import help_text, book_orig_text
from helpers.storage import users, abstracts, save, ignore
from helpers.timer import timer
from helpers.update_chat import migrate_to_chat_id, new_private_cr, setup_bot_handlers
from helpers.utils import n

content_types = ["text", "audio", "document", "photo", "sticker", "video", "video_note", "voice",
                 "location", "contact", "poll", "chat_member", "game", "dice"]


@bot.middleware_handler(['message'])
def chat_management(_, msg: Message):
    if str(msg.chat.id) not in ignore:  # copy messages to admin
        if str(msg.chat.id) != storage.current_chat:
            storage.current_chat = str(msg.chat.id)
            save()
            if msg.chat.type == "private":
                bot.send_message(admin_chat, "<b>" + str(msg.chat.first_name) + " " +
                                 str(msg.chat.id) + "</b>", 'HTML')
            else:
                bot.send_message(admin_chat, "<b>" + str(msg.from_user.first_name) + " " +
                                 str(msg.from_user.id) + "\n " + str(msg.chat.title) + " " +
                                 str(msg.chat.id) + "</b>", 'HTML')
        bot.copy_message(admin_chat, msg.chat.id, msg.id)
    transfer_to_other(msg)
    if msg.chat.type == "private" and users.get(str(msg.chat.id)) is None:
        new_private_cr(msg.chat)
        msg.new_user = True
    else:
        msg.new_user = False


@bot.message_handler(['start'])
def command_start(msg):
    if not msg.new_user:
        ai_talk(msg.text, str(msg.chat.id), start="О чём поговорим?🤔", send=True)


@bot.message_handler(['help'])
def command_help(msg: Message):
    bot.send_message(msg.chat.id, help_text, 'HTML')


@bot.message_handler(['books'])
def command_books(msg: Message):
    bot.send_message(msg.chat.id, book_orig_text, 'HTML',
                     reply_markup=quick_markup(
                         {grade: {'callback_data': f'btn_grade_{grade}'} for grade in abstracts}, 5))


@bot.message_handler(['id'])
def command_id(msg: Message):
    users[str(msg.chat.id)]['s'] = "getting_id"
    bot.send_message(msg.chat.id, "Теперь перешли мне любое сообщение из чата, "
                                  "или поделись со мной контактом этого человека.\n /cancel - отмена")
    save()


@bot.message_handler(['rnd'])
def command_rnd(msg: Message):
    nums = re.findall(r'\d+', msg.text)
    start_num = 1 if len(nums) < 2 else int(nums[0])
    end_num = 6 if len(nums) == 0 else int(nums[0]) if len(nums) == 1 else int(nums[1])
    if start_num > end_num:
        start_num, end_num = end_num, start_num
    bot.send_message(msg.chat.id,
                     f"🎲 Случайное число от {start_num} до {end_num}:  {random.randint(start_num, end_num)}")


done_cmd_handler = bot.message_handler(['done'])(done_cmd_handler)
chat_cmd_handler = bot.message_handler(['chat'])(chat_cmd_handler)
decode_cmd_handler = bot.message_handler(['d'])(decode_cmd_handler)
upscale_cmd_handler = bot.message_handler(['up'])(upscale_cmd_handler)
delete_cmd_handler = bot.message_handler(['delete'])(delete_cmd_handler)
weather_cmd_handler = bot.message_handler(['weather'])(weather_cmd_handler)
casino_cmd_handler = bot.message_handler(['casino'])(casino_cmd_handler)


@bot.message_handler(['kill_bot'])
def command_kill_bot(msg: Message):
    # kill bot (admin only)
    if msg.chat.id == admin_chat:
        bot.remove_webhook()
        bot.send_message(msg.chat.id, "Бот успешно отключен")
        print("bot killed")
        # noinspection PyProtectedMember
        os._exit(0)


@bot.message_handler(['exec'])
def command_exec(msg: Message):
    # exec command (admin only)
    if msg.chat.id == admin_chat:
        code_out = StringIO()
        sys.stdout = code_out
        try:
            exec(msg.text[6:])
        except Exception as e:
            bot.send_message(msg.chat.id, "ОШИБКА: " + str(e))
            return
        finally:
            sys.stdout = sys.__stdout__
        o = code_out.getvalue()
        if o == '':
            o = "Ничего не выведено"
        bot.send_message(msg.chat.id, o)


@bot.message_handler(['cancel'])
def command_cancel(msg: Message):
    if users[str(msg.chat.id)]['s']:
        users[str(msg.chat.id)]['s'] = ''
        users[str(msg.chat.id)].pop('sd', 0)
        bot.send_message(msg.chat.id, "<b>Всё отменяю!</b>", 'HTML', reply_markup=ReplyKeyboardRemove())
        save()
    else:
        try:
            end_chat(str(msg.chat.id))
        except ValueError:
            bot.send_message(msg.chat.id, "Я совершенно свободен", reply_markup=ReplyKeyboardRemove())


migrate_to_chat_id = bot.message_handler(content_types=["migrate_to_chat_id"])(migrate_to_chat_id)
edit_msg_handler = bot.edited_message_handler(content_types=content_types)(edit_msg_handler)

setup_bot_handlers()  # для обновления чатов (update_chat.py)


# @bot.message_handler(content_types=["user_shared"])
# def user_id_handler(msg: Message):
#     bot.send_message(msg.chat.id, msg.user_shared.user_id)
#
#
# @bot.message_handler(content_types=["chat_shared"])
# def chat_id_handler(msg: Message):
#     bot.send_message(msg.chat.id, msg.chat_shared.chat_id)
#

@bot.message_handler(content_types=content_types)
def chatting(msg: Message):
    current = str(n(msg.text) + n(msg.caption)).lower()
    args = re.split(r'[ ,.;&!?\[\]]+', current)
    # voter
    if msg.content_type == "poll":
        bot.send_message(msg.chat.id, random.choice(msg.poll.options).text, reply_to_message_id=msg.id)
    state = users[str(msg.chat.id)]['s']
    if state == "casino":
        casino_handler(msg)
        return
    if state == "balance":
        casino_balance_handler(msg)
        return
    if state == "wait_for_book_name":
        book_name_upload_state(msg)
        return
    elif state == "wait_for_book" or state == "wait_for_done":
        book_upload_state(msg)
        return
    elif state == "getting_id" or state == "wait_for_pub":
        wait_user_upload_state(msg, state)
        return
    elif state == "up_photo":
        wait_photo_state(msg)
        return
    elif state == "wait_for_city":
        search_city(msg)
        return
    if transfer_to_me(msg):  # если функция вернула True, то нужно выйти из основной функции
        return
    # image search
    if len(args) < 7 and any(s in current for s in searches):
        if msg.content_type == 'photo':
            photo_search(msg.chat.id, msg.id, msg.photo[-1])
            return
        elif msg.reply_to_message is not None and msg.reply_to_message.content_type == 'photo':
            photo_search(msg.chat.id, msg.reply_to_message.id, msg.reply_to_message.photo[-1])
            return

    if city_game_handler(str(msg.chat.id), current, args):
        return  # если функция вернула True, то нужно выйти из основной функции

    ai_talk(n(msg.text) + n(msg.caption), str(msg.chat.id), msg.chat.type == 'private', args, msg_voice=msg)


@bot.callback_query_handler(None)
def query(call: CallbackQuery):
    data = call.data
    if data.startswith("btn_complex"):
        inline_btn_complex_change(data, call)  # для игры в города (cities_game.py)
    elif data.startswith("btn_grade") or data.startswith("btn_subj_back"):
        grade_inline_section(data, call)  # хранилище конспектов (books_base.py)
    elif data.startswith("btn_subject") or data.startswith("btn_bok_back"):
        subject_inline_section(data, call)
    elif data.startswith("btn_book"):
        book_inline_section(data, call)
    elif data.startswith("btn_back"):
        bot.edit_message_text(book_orig_text, call.message.chat.id, call.message.message_id, parse_mode='HTML',
                              reply_markup=quick_markup({grade: {
                                  'callback_data': f'btn_grade_{grade}'} for grade in abstracts}, 5))
    elif data.startswith("btn_upload"):
        book_upload_button(data, call)
    elif data.startswith("btn_chat"):
        start_chat(str(call.message.chat.id), data[data.rfind("_") + 1:])
        bot.answer_callback_query(call.id, "Чат начат!")
    elif data.startswith("btn_photo"):
        profile_photo_button(data, call)
    elif data.startswith("btn_pinned"):
        pinned_msg_button(data, call)
    elif data.startswith("btn_change_city"):
        change_city_button(call.message.chat.id, call.message.chat.type)
        bot.answer_callback_query(call.id, "Введи свой город")
    elif data.startswith("btn_update_weather"):
        update_weather_button(call)
    elif data.startswith("btn_ignore"):
        ignore.append(data[data.rfind("_") + 1:])
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
        save()


inline_query_photo = bot.inline_handler(None)(inline_query_photo)

# Запуск бота
Thread(target=timer).start()
start_bot()

print("finish")
