from datetime import datetime

import ujson
from telebot.asyncio_filters import TextFilter
from telebot.asyncio_helper import ApiTelegramException
from telebot.service_utils import chunks
from telebot.types import Message, InlineKeyboardMarkup, \
    InlineKeyboardButton, InputMediaDocument, InputMediaPhoto, CallbackQuery
from telebot.util import quick_markup

from helpers.bot import bot
from helpers.db import BotDB
from helpers.long_texts import book_orig_text
from helpers.timer import ZoneInfo
from helpers.utils import n
from collections import Counter


def register_books_handler():
    bot.register_callback_query_handler(grade_inline_section, None,
                                        text=TextFilter(starts_with=['btn_grade', 'btn_subj_back']))
    bot.register_callback_query_handler(subject_inline_section, None,
                                        text=TextFilter(starts_with='btn_subject'))
    bot.register_callback_query_handler(book_inline_section, None,
                                        text=TextFilter(starts_with='btn_book'))
    bot.register_callback_query_handler(btn_books_back, None,
                                        text=TextFilter(starts_with='btn_back'))


async def get_home_markup():
    return quick_markup(
        {grade[0]: {'callback_data': f'btn_grade_{grade[0]}'} for grade in
         await BotDB.fetchall("SELECT DISTINCT `grade` FROM `books`")}, 5)


@bot.message_handler(['books'])
async def command_books(msg: Message):
    await bot.send_message(
        msg.chat.id, book_orig_text, reply_markup=await get_home_markup())


# @bot.message_handler(['done'])
# def done_cmd_handler(msg: Message):
#     if users[str(msg.chat.id)]['s'] == "wait_for_done":
#         users[str(msg.chat.id)]['s'] = "wait_for_pub"
#         users[str(msg.chat.id)]['sd']['z'] = str(msg.chat.id)
#         markup = ReplyKeyboardMarkup(
#             input_field_placeholder="Чей конспект?", row_width=1, resize_keyboard=True).add(
#             KeyboardButton(
#                 f'{msg.from_user.id}; {msg.from_user.first_name + n(msg.from_user.last_name, " ")}  (вы)'),
#             *[KeyboardButton(f'{a}; {name}') for a, name in users[str(msg.chat.id)]['sd']['a'].items()])
#         bot.send_message(
#             msg.chat.id,
#             "От имени кого ты хочешь выложить конспект?\nВыбери внизу, или поделись со мной "
#             "контактом этого человека, или перешли от него любое сообщение, или напиши его имя",
#             reply_markup=markup)
#         save()
#     elif users[str(msg.chat.id)]['s'] == "wait_for_pub":
#         book_data = users[str(msg.chat.id)]['sd']
#         grade, subject, book = book_data['data']
#         unix = book_data['d'] if 'd' in book_data else msg.date
#         book = f'{book} ({datetime.fromtimestamp(unix, ZoneInfo("Europe/Moscow")).year})'
#         abstracts[grade][subject].append({'n': book, 'id': book_data['id'], 'a': book_data['z'], 't': unix})
#         bot.send_message(msg.chat.id,
#                          f'<b>Ваш конспект "{book}" успешно выложен!\n🎓 {grade} класс, {subject}</b>',
#                          reply_markup=ReplyKeyboardRemove())
#         users[str(msg.chat.id)]['s'] = ''
#         users[str(msg.chat.id)].pop('sd')
#         save()
async def btn_books_back(call: CallbackQuery):
    await bot.edit_message_text(book_orig_text, call.message.chat.id, call.message.message_id,
                                reply_markup=await get_home_markup())


async def grade_inline_section(call: CallbackQuery):
    grade = call.data[call.data.rfind("_") + 1:]
    markup = {"◀ Назад": {'callback_data': 'btn_back'}}

    subjects = await BotDB.fetchall("SELECT `subject` FROM `books` WHERE `grade` = %s", grade)
    counter = Counter([s[0] for s in subjects])

    markup.update({f'{subject} ({count})': {
        'callback_data': f'btn_subject_{grade}_{subject}'} for subject, count in counter.items()})
    await bot.edit_message_text(
        "<b>📕Конспекты и готовые билеты📙</b>\n\n"
        f"<b>🎓 Класс:</b> {grade}\nТеперь выберите нужный предмет, "
        "чтобы <i>найти</i> нужный конспект", call.message.chat.id, call.message.id,
        reply_markup=quick_markup(markup))


async def subject_inline_section(call: CallbackQuery):
    fs = call.data.rfind("_")
    subject = call.data[fs + 1:]
    grade = call.data[call.data[:fs].rfind("_") + 1:fs]

    books = await BotDB.fetchall("SELECT `name` FROM `books` WHERE `grade` = %s AND `subject` = %s",
                                 (grade, subject))

    markup = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("◀ Назад", callback_data=f'btn_subj_back_{grade}'),
        InlineKeyboardButton("Обновить 🔄️", callback_data=f'btn_subject_{grade}_{subject}'),
        # InlineKeyboardButton("Выложить 🔼", callback_data=f'btn_upload_{grade}_{subject}'),
        row_width=2).add(
        *[InlineKeyboardButton(name[0], callback_data=f'btn_book_{grade}_{subject}_{name[0]}') for name in books])
    try:
        await bot.edit_message_text(
            f"<b>📕Конспекты и готовые билеты📙</b>\n\n<b>🎓 Класс:</b> {grade}\n<b>📗 {subject}</b>\n\n"
            f"<b>Найдено конспектов:</b> {len(books)}",
            call.message.chat.id, call.message.id, reply_markup=markup)
    except ApiTelegramException:
        await bot.answer_callback_query(call.id, "Ничего нового😥", show_alert=True, cache_time=5)


async def book_inline_section(call: CallbackQuery):
    _, _, grade, subject, book = call.data.split("_")
    _, _, _, _, author_name, timestamp, data_doc, data_photo, data_url = await BotDB.fetchone(
        "SELECT * FROM `books` WHERE `grade` = %s AND `subject` = %s AND `name` = %s", (grade, subject, book))
    try:
        author = await bot.get_chat(int(author_name))
        author_name = f'<a href="tg://user?id={author_name}">' \
                      f'{author.first_name + n(author.last_name, " ")}</a> {n(author.username, "@")}'
    except (ApiTelegramException, ValueError):
        pass
    docs = [InputMediaDocument(d, parse_mode='HTML') for d in ujson.loads(data_doc)]
    photos = [InputMediaPhoto(d, parse_mode='HTML') for d in ujson.loads(data_photo)]
    caption = f'{data_url}<b>{book}\nАвтор: {author_name}\nОпубликовано: ' \
              f'{datetime.fromtimestamp(timestamp, ZoneInfo("Europe/Moscow")).strftime("%d.%m.%Y %H:%M")}</b>'
    if len(docs) > 0:
        docs[-1].caption = caption
    elif len(photos) > 0:
        photos[-1].caption = caption
    else:
        await bot.send_message(call.message.chat.id, caption)
    for chunk in chunks(photos, 10):
        await bot.send_media_group(call.message.chat.id, chunk)
    for chunk in chunks(docs, 10):
        await bot.send_media_group(call.message.chat.id, chunk)
    await bot.answer_callback_query(call.id, "Конспект отправлен!")

# def book_upload_button(data, call):
#     fs = data.rfind("_")
#     subject = data[fs + 1:]
#     grade = data[data[:fs].rfind("_") + 1:fs]
#     bot.send_message(
#         call.message.chat.id,
#         f'<b>🎓 Класс:</b> {grade}\n<b>📗 {subject}</b>\n\n'
#         f'<b>Чтобы выложить свой конспект, напиши его <i>название</i></b> '
#         f'<i>(год будет подписан автоматически в его конце)</i>\n<i>/cancel - отмена</i>',
#         reply_markup=ForceReply(input_field_placeholder="Введи название конспекта"))
#     bot.answer_callback_query(call.id, "Следуй инструкциям!")
#     users[str(call.message.chat.id)]['s'] = "wait_for_book_name"
#     users[str(call.message.chat.id)]['sd'] = (grade, subject)
#     save()
#
#
# def book_name_upload_state(msg: Message):
#     name = n(msg.text) + n(msg.caption)
#     if name:
#         grade, subject = users[str(msg.chat.id)]['sd']
#         users[str(msg.chat.id)]['s'] = "wait_for_book"
#         users[str(msg.chat.id)]['sd'] = {'id': {'d': [], 'p': [], 'u': ''}, 'data': (grade, subject, name),
#                                          'a': {}, 'g': ''}
#         bot.send_message(msg.chat.id, f"Конспект успешно назван: <b>{name}</b>")
#         bot.send_message(msg.chat.id, f"<b>Теперь отправь файлы, фото, или ссылку с готовым конспектом</b>",
#                          reply_markup=ForceReply(input_field_placeholder="Отправь конспект"))
#         save()
#     else:
#         bot.send_message(msg.chat.id, "Попробуй назвать свой конспект ещё раз нормально")
#
#
# def book_upload_state(msg: Message):
#     if msg.content_type == "photo":
#         users[str(msg.chat.id)]['sd']['id']['p'].append(msg.photo[-1].file_id)
#     elif msg.content_type == "document":
#         users[str(msg.chat.id)]['sd']['id']['d'].append(msg.document.file_id)
#     elif msg.content_type == "text" and msg.entities is not None and any(e.type == 'url' for e in msg.entities):
#         users[str(msg.chat.id)]['sd']['id']['u'] += msg.text + '\n\n'
#     else:
#         bot.send_message(msg.chat.id, "<b>В конспекты можно отправлять только файлы, "
#                                       "ссылки, фото или фото без сжатия!</b>")
#         save()
#         return
#     if msg.forward_from is not None:
#         if msg.forward_from.id != msg.from_user.id:
#             users[str(msg.chat.id)]['sd']['a'][
#                 msg.forward_from.id] = msg.forward_from.first_name + n(msg.forward_from.last_name, " ")
#         users[str(msg.chat.id)]['sd']['d'] = msg.forward_date
#     if msg.media_group_id is None or msg.media_group_id != users[str(msg.chat.id)]['sd']['g']:
#         users[str(msg.chat.id)]['s'] = "wait_for_done"
#         bot.send_message(msg.chat.id, "<b>Чтобы выложить конспект, используй команду /done</b>")
#     users[str(msg.chat.id)]['sd']['g'] = msg.media_group_id
#     save()
#
#
# def wait_user_upload_state(msg: Message, state):  # TODO код надо переделать
#     is_pub = state == "wait_for_pub"
#     if is_pub:
#         markup = None
#     else:
#         users[str(msg.chat.id)]['s'] = ''
#         save()
#         markup = InlineKeyboardMarkup()
#     if msg.content_type == 'contact':
#         chat_id = msg.contact.user_id
#         if not chat_id:
#             bot.send_message(msg.chat.id, "Этого человека нет в Telegram.")
#         else:
#             if is_pub:
#                 author_name = f'<a href="tg://user?id={chat_id}">' \
#                               f'{msg.contact.first_name + n(msg.contact.last_name, " ")}</a>'
#                 bot.send_message(
#                     msg.chat.id, f"Конспект будет выложен от: <b>{author_name}</b> ?\n/done - выложить")
#                 users[str(msg.chat.id)]['sd']['z'] = str(chat_id)
#                 save()
#             else:
#                 markup.add(InlineKeyboardButton(text="Начать чат", callback_data=f"btn_chat_{chat_id}"))
#                 bot.send_message(msg.chat.id, chat_id, reply_markup=markup)
#     elif msg.forward_from is not None:
#         chat_id = msg.forward_from.id
#         if is_pub:
#             author_name = f'<a href="tg://user?id={chat_id}">' \
#                           f'{msg.forward_from.first_name + n(msg.forward_from.last_name, " ")}</a>' \
#                           f' {n(msg.forward_from.username, "@")}'
#             bot.send_message(msg.chat.id, f"Конспект будет выложен от: <b>{author_name}</b>\n"
#                                           f"/done - выложить")
#             users[str(msg.chat.id)]['sd']['z'] = str(chat_id)
#             save()
#         else:
#             markup.add(InlineKeyboardButton(text="Начать чат", callback_data=f"btn_chat_{chat_id}"))
#             bot.send_message(msg.chat.id, chat_id, reply_markup=markup)
#     elif is_pub:
#         if msg.content_type == 'text':
#             name = msg.text
#             chat_id = name
#             ids = name.find('; ')
#             if ids != -1:
#                 chat_id = name[:ids]
#                 name = name[ids + 2:]
#             bot.send_message(msg.chat.id, f"Конспект будет выложен от: <b>{name}</b> ?\n"
#                                           f"/done - выложить")
#             users[str(msg.chat.id)]['sd']["z"] = chat_id
#             save()
#         else:
#             bot.send_message(msg.chat.id, "Попробуй ещё раз")
