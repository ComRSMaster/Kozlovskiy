from datetime import datetime

from telebot.apihelper import ApiTelegramException
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, Message, InlineKeyboardMarkup, \
    InlineKeyboardButton, InputMediaDocument, InputMediaPhoto, ForceReply
from telebot.util import quick_markup

from helpers.bot import bot
from helpers.db import BotDB
from helpers.long_texts import book_orig_text
from helpers.timer import ZoneInfo
from helpers.utils import n


@bot.message_handler(['books'])
async def command_books(msg: Message):
    await bot.send_message(
        msg.chat.id, book_orig_text, reply_markup=quick_markup(
            {grade[0]: {'callback_data': f'btn_grade_{grade[0]}'} for grade in
             await BotDB.fetchall("SELECT DISTINCT `grade` FROM `books`")}, 5))


@bot.message_handler(['done'])
def done_cmd_handler(msg: Message):
    if users[str(msg.chat.id)]['s'] == "wait_for_done":
        users[str(msg.chat.id)]['s'] = "wait_for_pub"
        users[str(msg.chat.id)]['sd']['z'] = str(msg.chat.id)
        markup = ReplyKeyboardMarkup(
            input_field_placeholder="Чей конспект?", row_width=1, resize_keyboard=True).add(
            KeyboardButton(
                f'{msg.from_user.id}; {msg.from_user.first_name + n(msg.from_user.last_name, " ")}  (вы)'),
            *[KeyboardButton(f'{a}; {name}') for a, name in users[str(msg.chat.id)]['sd']['a'].items()])
        bot.send_message(
            msg.chat.id,
            "От имени кого ты хочешь выложить конспект?\nВыбери внизу, или поделись со мной "
            "контактом этого человека, или перешли от него любое сообщение, или напиши его имя",
            reply_markup=markup)
        save()
    elif users[str(msg.chat.id)]['s'] == "wait_for_pub":
        book_data = users[str(msg.chat.id)]['sd']
        grade, subject, book = book_data['data']
        unix = book_data['d'] if 'd' in book_data else msg.date
        book = f'{book} ({datetime.fromtimestamp(unix, ZoneInfo("Europe/Moscow")).year})'
        abstracts[grade][subject].append({'n': book, 'id': book_data['id'], 'a': book_data['z'], 't': unix})
        bot.send_message(msg.chat.id,
                         f'<b>Ваш конспект "{book}" успешно выложен!\n🎓 {grade} класс, {subject}</b>',
                         reply_markup=ReplyKeyboardRemove())
        users[str(msg.chat.id)]['s'] = ''
        users[str(msg.chat.id)].pop('sd')
        save()


def grade_inline_section(data, call):
    grade = data[data.rfind("_") + 1:]
    subjects = {"◀ Назад": {'callback_data': 'btn_back'}}
    subjects.update({f'{subject} ({len(abstracts[grade][subject])})': {
        'callback_data': f'btn_subject_{grade}_{subject}'} for subject in abstracts[grade]})
    bot.edit_message_text(
        "<b>📕Конспекты и готовые билеты📙</b>\n\n"
        f"<b>🎓 Класс:</b> {grade}\nТеперь выберите нужный предмет, "
        "чтобы <i>найти</i> или <i>выложить</i> нужный конспект", call.message.chat.id, call.message.message_id,
        chat_id, reply_markup=quick_markup(subjects))


def subject_inline_section(data, call):
    fs = data.rfind("_")
    subject = data[fs + 1:]
    grade = data[data[:fs].rfind("_") + 1:fs]
    markup = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("◀ Назад", callback_data=f'btn_subj_back_{grade}'),
        InlineKeyboardButton("Обновить 🔄️", callback_data=f'btn_subject_{grade}_{subject}'),
        InlineKeyboardButton(
            "Выложить 🔼", callback_data=f'btn_upload_{grade}_{subject}'), row_width=3).add(
        *[InlineKeyboardButton(
            abstracts[grade][subject][b]["n"],
            callback_data=f'btn_book_{grade}_{subject}_{b}') for b in range(len(abstracts[grade][subject]))])
    try:
        bot.edit_message_text(
            f"<b>📕Конспекты и готовые билеты📙</b>\n\n<b>🎓 Класс:</b> {grade}\n<b>📗 {subject}</b>\n\n"
            f"<b>Найдено конспектов:</b> {len(abstracts[grade][subject])}\n<i>Также ты можешь выложить свой "
            f"конспект</i>", call.message.chat.id, call.message.message_id, chat_id, reply_markup=markup)
    except ApiTelegramException:
        bot.answer_callback_query(call.id, "Ничего нового😥", show_alert=True, cache_time=5)


def book_inline_section(data, call):
    _, _, grade, subject, book = data.split("_")
    info = abstracts[grade][subject][int(book)]
    author_name = info["a"]
    try:
        author = bot.get_chat(int(author_name))
        author_name = f'<a href="tg://user?id={info["a"]}">' \
                      f'{author.first_name + n(author.last_name, " ")}</a> {n(author.username, "@")}'
    except (ApiTelegramException, ValueError):
        pass
    docs = [InputMediaDocument(d) for d in info['id']['d']]
    photos = [InputMediaPhoto(d) for d in info['id']['p']]
    caption = f'{info["id"]["u"]}<b>{info["n"]}\nАвтор: {author_name}\nОпубликовано: ' \
              f'{datetime.fromtimestamp(info["t"], ZoneInfo("Europe/Moscow")).strftime("%d.%m.%Y %H:%M")}</b>'
    if len(docs) > 0:
        docs[-1].caption = caption
    elif len(photos) > 0:
        photos[-1].caption = caption
    else:
        bot.send_message(call.message.chat.id, caption)
    for i in range(0, len(photos), 10):
        bot.send_media_group(call.message.chat.id, photos[i:i + 10])
    for i in range(0, len(docs), 10):
        bot.send_media_group(call.message.chat.id, docs[i:i + 10])
    bot.answer_callback_query(call.id, "Конспект отправлен!")


def book_upload_button(data, call):
    fs = data.rfind("_")
    subject = data[fs + 1:]
    grade = data[data[:fs].rfind("_") + 1:fs]
    bot.send_message(
        call.message.chat.id,
        f'<b>🎓 Класс:</b> {grade}\n<b>📗 {subject}</b>\n\n'
        f'<b>Чтобы выложить свой конспект, напиши его <i>название</i></b> '
        f'<i>(год будет подписан автоматически в его конце)</i>\n<i>/cancel - отмена</i>',
        reply_markup=ForceReply(input_field_placeholder="Введи название конспекта"))
    bot.answer_callback_query(call.id, "Следуй инструкциям!")
    users[str(call.message.chat.id)]['s'] = "wait_for_book_name"
    users[str(call.message.chat.id)]['sd'] = (grade, subject)
    save()


def book_name_upload_state(msg: Message):
    name = n(msg.text) + n(msg.caption)
    if name:
        grade, subject = users[str(msg.chat.id)]['sd']
        users[str(msg.chat.id)]['s'] = "wait_for_book"
        users[str(msg.chat.id)]['sd'] = {'id': {'d': [], 'p': [], 'u': ''}, 'data': (grade, subject, name),
                                         'a': {}, 'g': ''}
        bot.send_message(msg.chat.id, f"Конспект успешно назван: <b>{name}</b>")
        bot.send_message(msg.chat.id, f"<b>Теперь отправь файлы, фото, или ссылку с готовым конспектом</b>",
                         reply_markup=ForceReply(input_field_placeholder="Отправь конспект"))
        save()
    else:
        bot.send_message(msg.chat.id, "Попробуй назвать свой конспект ещё раз нормально")


def book_upload_state(msg: Message):
    if msg.content_type == "photo":
        users[str(msg.chat.id)]['sd']['id']['p'].append(msg.photo[-1].file_id)
    elif msg.content_type == "document":
        users[str(msg.chat.id)]['sd']['id']['d'].append(msg.document.file_id)
    elif msg.content_type == "text" and msg.entities is not None and any(e.type == 'url' for e in msg.entities):
        users[str(msg.chat.id)]['sd']['id']['u'] += msg.text + '\n\n'
    else:
        bot.send_message(msg.chat.id, "<b>В конспекты можно отправлять только файлы, "
                                      "ссылки, фото или фото без сжатия!</b>")
        save()
        return
    if msg.forward_from is not None:
        if msg.forward_from.id != msg.from_user.id:
            users[str(msg.chat.id)]['sd']['a'][
                msg.forward_from.id] = msg.forward_from.first_name + n(msg.forward_from.last_name, " ")
        users[str(msg.chat.id)]['sd']['d'] = msg.forward_date
    if msg.media_group_id is None or msg.media_group_id != users[str(msg.chat.id)]['sd']['g']:
        users[str(msg.chat.id)]['s'] = "wait_for_done"
        bot.send_message(msg.chat.id, "<b>Чтобы выложить конспект, используй команду /done</b>")
    users[str(msg.chat.id)]['sd']['g'] = msg.media_group_id
    save()


def wait_user_upload_state(msg: Message, state):  # TODO код говно, надо переделать
    is_pub = state == "wait_for_pub"
    if is_pub:
        markup = None
    else:
        users[str(msg.chat.id)]['s'] = ''
        save()
        markup = InlineKeyboardMarkup()
    if msg.content_type == 'contact':
        chat_id = msg.contact.user_id
        if not chat_id:
            bot.send_message(msg.chat.id, "Этого человека нет в Telegram.")
        else:
            if is_pub:
                author_name = f'<a href="tg://user?id={chat_id}">' \
                              f'{msg.contact.first_name + n(msg.contact.last_name, " ")}</a>'
                bot.send_message(
                    msg.chat.id, f"Конспект будет выложен от: <b>{author_name}</b> ?\n/done - выложить")
                users[str(msg.chat.id)]['sd']['z'] = str(chat_id)
                save()
            else:
                markup.add(InlineKeyboardButton(text="Начать чат", callback_data=f"btn_chat_{chat_id}"))
                bot.send_message(msg.chat.id, chat_id, reply_markup=markup)
    elif msg.forward_from is not None:
        chat_id = msg.forward_from.id
        if is_pub:
            author_name = f'<a href="tg://user?id={chat_id}">' \
                          f'{msg.forward_from.first_name + n(msg.forward_from.last_name, " ")}</a>' \
                          f' {n(msg.forward_from.username, "@")}'
            bot.send_message(msg.chat.id, f"Конспект будет выложен от: <b>{author_name}</b>\n"
                                          f"/done - выложить")
            users[str(msg.chat.id)]['sd']['z'] = str(chat_id)
            save()
        else:
            markup.add(InlineKeyboardButton(text="Начать чат", callback_data=f"btn_chat_{chat_id}"))
            bot.send_message(msg.chat.id, chat_id, reply_markup=markup)
    elif is_pub:
        if msg.content_type == 'text':
            name = msg.text
            chat_id = name
            ids = name.find('; ')
            if ids != -1:
                chat_id = name[:ids]
                name = name[ids + 2:]
            bot.send_message(msg.chat.id, f"Конспект будет выложен от: <b>{name}</b> ?\n"
                                          f"/done - выложить")
            users[str(msg.chat.id)]['sd']["z"] = chat_id
            save()
        else:
            bot.send_message(msg.chat.id, "Попробуй ещё раз")
