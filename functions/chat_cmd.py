from telebot.apihelper import ApiTelegramException
from telebot.types import Chat, Message, InlineQuery, InlineQueryResultArticle, InputTextMessageContent, InputMediaPhoto
from telebot.util import quick_markup, extract_arguments, chunks

from helpers.bot import bot
from helpers.config import web_url
from helpers.long_texts import chat_cmd_desc
from helpers.storage import chat_msg_pen, chat_msg_my, current_users, chat_id_pen, chat_id_my, save, users, images
from helpers.utils import n


def chat_cmd_handler(msg: Message):
    chat_id = extract_arguments(msg.text)
    if chat_id:
        start_chat(str(msg.chat.id), chat_id)
    else:
        bot.send_message(
            msg.chat.id, chat_cmd_desc, "HTML",
            reply_markup=quick_markup({'Выбрать чат 💬': {'switch_inline_query_current_chat': ''}}))
        # bot.send_message(
        #     msg.chat.id, "", "HTML",
        #     reply_markup=ReplyKeyboardMarkup(True).add(
        #         KeyboardButton(
        #             "Выбрать пользователя", request_user=KeyboardButtonRequestUser(
        #                 random.randint(-2147483640, 2147483640), False)),
        #         KeyboardButton(
        #             "Выбрать группу", request_chat=KeyboardButtonRequestChat(
        #                 random.randint(-2147483640, 2147483640), False))))


def inline_query_photo(inline_query: InlineQuery):
    results = []
    index = 0
    for u in users:
        index += 1
        results.append(InlineQueryResultArticle(
            index, users[u]['name'], InputTextMessageContent("/chat " + u),
            description=users[u]['desc'] + "\nНажмите, чтобы написать " + (
                "этому человеку" if users[u]['private'] else "в эту группу"),
            thumb_url=None if users[u]['photo_id'] is None else f'{web_url}p/{users[u]["photo_id"]}.jpg'))
    bot.answer_inline_query(inline_query.id, results)


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
                         reply_markup=quick_markup(elem, row_width=3))
        chat_id_my.append(chat_id)
        chat_id_pen.append(chat)
        current_users.append("")
        chat_msg_my.append([])
        chat_msg_pen.append([])
        save()
    except ApiTelegramException:
        bot.send_message(chat_id, "<b>Чат не найден</b>", 'HTML')


def parse_chat(chat: Chat):
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
        except ApiTelegramException:
            pass
    return text


def profile_photo_button(data, call):
    chat_id = data[data.rfind("_") + 1:]
    try:
        chat_info = bot.get_chat(chat_id)
    except ApiTelegramException:
        bot.answer_callback_query(call.id, "Чат не найден!")
        return
    if chat_info.photo is None:
        bot.answer_callback_query(call.id, "Фото профиля не найдены!")
        return
    if chat_info.type == "private":
        profile_photos: list = bot.get_user_profile_photos(int(chat_id)).photos
        media_group = []
        k = 0
        for c in chunks(profile_photos, 10):
            bot.send_chat_action(call.message.chat.id, action="upload_photo")
            for p in c:
                k += 1
                media_group.append(InputMediaPhoto(
                    images[p[-1].file_id] if p[-1].file_id in images else
                    bot.download_file(bot.get_file(p[-1].file_id).file_path)))
            sent_photos = bot.send_media_group(call.message.chat.id, media_group)
            for i in range(len(sent_photos)):
                images[profile_photos[k - len(c) + i][-1].file_id] = sent_photos[i].photo[-1].file_id
            media_group.clear()
    else:
        bot.send_chat_action(call.message.chat.id, action="upload_photo")
        file_id = chat_info.photo.big_file_id
        photo_id = images[file_id] if file_id in images else bot.download_file(bot.get_file(file_id).file_path)
        images[file_id] = bot.send_photo(call.message.chat.id, photo_id).photo[-1].file_id
    bot.answer_callback_query(call.id, "Фото отправлены!")
    save()


def pinned_msg_button(data, call):
    forward = data.split("_")
    try:
        bot.forward_message(call.message.chat.id, forward[2], int(forward[3]))
    except ApiTelegramException:
        try:
            bot.send_message(call.message.chat.id, f"<b>Закреп от: {forward[4]}</b>", 'HTML')
            bot.copy_message(call.message.chat.id, forward[2], int(forward[3]))
        except ApiTelegramException:
            bot.answer_callback_query(call.id, "Сообщение не закреплено!")
            return
    bot.answer_callback_query(call.id, "Закреп отправлен!")


def todict(obj):
    data = {}
    for key, value in obj.__dict__.items():
        try:
            data[key] = todict(value)
        except AttributeError:
            data[key] = value
    return data


def transfer_to_me(msg: Message):
    try:
        my_index = chat_id_my.index(str(msg.chat.id))  # мы
        reply = None
        try:
            reply = chat_msg_pen[my_index][chat_msg_my[my_index].index(msg.reply_to_message.message_id)]
        except AttributeError:
            pass
        chat_msg_my[my_index].append(msg.id)
        chat_msg_pen[my_index].append(bot.copy_message(chat_id_pen[my_index], msg.chat.id, msg.id,
                                                       reply_to_message_id=reply).message_id)
        save()
        return True
    except ApiTelegramException as err:
        bot.send_message(msg.chat.id, "<b>Этому человеку невозможно написать через Козловского.</b>"
                                      "<i>(" + str(err.description) + ")</i>", 'HTML')
        return True
    except ValueError:
        pass
    return False


def transfer_to_other(msg: Message):
    try:
        for other_index in range(len(chat_id_pen)):
            if chat_id_pen[other_index] != str(msg.chat.id):  # собеседники
                continue
            if msg.chat.type != "private":
                if str(msg.from_user.id) not in current_users[other_index]:
                    current_users[other_index] = str(msg.from_user.id)
                    bot.send_message(chat_id_my[other_index], "<b>" + str(msg.from_user.first_name) + " <pre>" +
                                     str(msg.from_user.id) + "</pre></b>", 'HTML')
            reply = None
            try:
                reply = chat_msg_my[other_index][chat_msg_pen[other_index].index(msg.reply_to_message.message_id)]
            except AttributeError:
                pass
            chat_msg_my[other_index].append(
                bot.copy_message(chat_id_my[other_index], msg.chat.id, msg.id, reply_to_message_id=reply).message_id)
            chat_msg_pen[other_index].append(msg.id)
            save()
    except ValueError:
        pass


def edit_msg_handler(msg: Message):
    try:
        my_index = chat_id_my.index(str(msg.chat.id))
        bot.edit_message_text(msg.text, chat_id_pen[my_index],
                              chat_msg_pen[my_index][chat_msg_my[my_index].index(msg.id)])
    except ValueError:
        pass
    try:
        other_index = chat_id_pen.index(str(msg.chat.id))
        bot.edit_message_text(msg.text, chat_id_my[other_index],
                              chat_msg_my[other_index][chat_msg_pen[other_index].index(msg.id)])
    except ValueError:
        pass


def delete_cmd_handler(msg: Message):
    try:
        reply = msg.reply_to_message.message_id
        my_index = chat_id_my.index(str(msg.chat.id))
        bot.delete_message(chat_id_pen[my_index], chat_msg_pen[my_index][chat_msg_my[my_index].index(reply)])
        bot.send_message(msg.chat.id, "<i>Сообщение удалено.</i>", 'HTML')
    except AttributeError:
        bot.send_message(msg.chat.id, "Ответьте командой /delete на сообщение, которое требуется удалить.")
    except ApiTelegramException:
        bot.send_message(msg.chat.id, "<i>Не удалось удалить сообщение.</i>", 'HTML')
    except ValueError:
        pass


def end_chat(chat_id):
    my_index = chat_id_my.index(chat_id)
    chat_id_my.pop(my_index)
    chat_id_pen.pop(my_index)
    chat_msg_my.pop(my_index)
    chat_msg_pen.pop(my_index)
    current_users.pop(my_index)
    bot.send_message(chat_id, "Конец переписки")
    save()
