from asyncio import ensure_future

from telebot.asyncio_filters import TextFilter
from telebot.asyncio_handler_backends import ContinueHandling
from telebot.asyncio_helper import ApiTelegramException
from telebot.types import Chat, Message, InlineQuery, InlineQueryResultArticle, InputTextMessageContent, \
    InputMediaPhoto, CallbackQuery, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telebot.util import quick_markup, chunks, content_type_media, extract_arguments

from helpers.bot import bot
from helpers.config import web_url
from helpers.long_texts import chat_cmd_desc
from helpers.db import BotDB
from helpers.user_states import States
from helpers.utils import n, user_link


def register_chat_handler():
    bot.register_message_handler(chat_cmd_handler, commands=['chat'])
    bot.register_message_handler(delete_cmd_handler, commands=['delete'])
    bot.register_message_handler(end_chat, state=States.CHATTING, commands=['cancel'])
    bot.register_message_handler(getting_id, state=States.GETTING_ID, content_types=content_type_media)
    bot.register_message_handler(transfer_to_target, state=States.CHATTING, content_types=content_type_media)

    bot.register_callback_query_handler(profile_photo_button, None, text=TextFilter(starts_with='btn_photo'))
    bot.register_callback_query_handler(pinned_msg_button, None, text=TextFilter(starts_with='btn_pinned'))

    bot.register_edited_message_handler(edit_msg_handler, content_types=content_type_media)
    bot.register_inline_handler(inline_query_photo, None)


async def chat_cmd_handler(msg: Message):
    chat_id = extract_arguments(msg.text)
    if chat_id:
        await start_chat(msg.chat.id, chat_id)
    else:
        await bot.send_message(
            msg.chat.id, chat_cmd_desc,
            reply_markup=quick_markup({'Выбрать чат 💬': {'switch_inline_query_current_chat': ''}}))
        # bot.send_message(
        #     msg.chat.id, "",
        #     reply_markup=ReplyKeyboardMarkup(True).add(
        #         KeyboardButton(
        #             "Выбрать пользователя", request_user=KeyboardButtonRequestUser(
        #                 random.randint(-2147483640, 2147483640), False)),
        #         KeyboardButton(
        #             "Выбрать группу", request_chat=KeyboardButtonRequestChat(
        #                 random.randint(-2147483640, 2147483640), False))))


async def inline_query_photo(inline_query: InlineQuery):
    results = []
    offset = int(inline_query.offset) if inline_query.offset else 0
    query = f'%{inline_query.query}%'

    for u in await BotDB.fetchall(
            "SELECT `id`, `name`, `desc`, `photo_id`, `is_private` FROM `users`"
            "WHERE `only_chess` = 0 AND (`name` LIKE %s OR `desc` LIKE %s)"
            "ORDER BY `name` LIMIT %s, %s", (query, query, offset, 50)):
        results.append(InlineQueryResultArticle(
            u[0], u[1] or ' ', InputTextMessageContent(f"/chat {u[0]}"),
            description=f"{u[2] or ''}\nНажмите, чтобы написать {'этому человеку' if u[4] else 'в эту группу'}",
            thumbnail_url=None if u[3] is None else f'{web_url}p/{u[3]}.jpg'))

    await bot.answer_inline_query(inline_query.id, results,
                                  next_offset='' if len(results) != 50 else int(offset) + 50)


async def start_chat(chat_id: int, target_chat: str):
    try:
        target_chat = int(target_chat)

        if target_chat == chat_id:
            await bot.send_message(chat_id, "<b>Нельзя писать самому себе через Козловского.</b>")
            return

        chat_info = await bot.get_chat(target_chat)
    except (ApiTelegramException, ValueError):
        await bot.send_message(chat_id, "<b>Чат не найден</b>")
        return

    markup = {}
    if chat_info.photo is not None:
        markup["Посмотреть фото профиля"] = {'callback_data': f"btn_photo_{target_chat}"}

    p_msg = chat_info.pinned_message
    if p_msg is not None:
        markup["Посмотреть закреп"] = {
            'callback_data': f"btn_pinned_{p_msg.chat.id}_{p_msg.message_id}_{p_msg.from_user.first_name}"}

    await bot.send_message(chat_id, await parse_chat(chat_info) +
                           "\n\n<b>/cancel - закончить переписку\n/delete - удалить сообщение у собеседника</b>",
                           reply_markup=quick_markup(markup, 1))
    await BotDB.execute("INSERT INTO chats (initiator, target) VALUES (%s, %s)", (chat_id, target_chat))
    await BotDB.set_state(chat_id, States.CHATTING, target_chat)


async def parse_chat(chat: Chat):
    text = ""
    if chat.type == "private":
        text += f'<b>Начат чат с<a href="tg://user?id={chat.id}">: {chat.first_name}' + \
                n(chat.last_name, ' ') + '</a></b>' + n(chat.bio, '\n<b>Описание:</b> ') + n(chat.username, '\n@')
    elif chat.type == "channel":
        return str(todict(chat))
    else:
        text += f'<b>Начат чат с группой:</b> {chat.title}' + n(chat.description, '\n<b>Описание:</b> ') + \
                n(chat.username, '\n@') + n(chat.invite_link, '\n<b>Ссылка:</b> ')
        try:
            text += f'\n<b>Участников:</b> {await bot.get_chat_member_count(chat.id)}\n<b>Админы:</b> '
            for m in await bot.get_chat_administrators(chat.id):
                text += '\n\n' + user_link(m.user, True) + n(m.user.username, ' @')
        except ApiTelegramException:
            pass
    return text


async def profile_photo_button(call: CallbackQuery):
    chat_id = int(call.data[call.data.rfind("_") + 1:])
    try:
        chat_info = await bot.get_chat(chat_id)
    except ApiTelegramException:
        await bot.answer_callback_query(call.id, "Чат не найден!")
        return
    if chat_info.photo is None:
        await bot.answer_callback_query(call.id, "Фото профиля не найдены!")
        return

    if chat_info.type == "private":
        profile_photos = (await bot.get_user_profile_photos(chat_id)).photos

        for chunk in chunks(profile_photos, 10):
            media_group = [InputMediaPhoto(p[-1].file_id) for p in chunk]
            ensure_future(bot.send_media_group(call.message.chat.id, media_group))
    else:
        await bot.send_photo(call.message.chat.id,
                             await bot.download_file((await bot.get_file(chat_info.photo.big_file_id)).file_path))
    await bot.answer_callback_query(call.id, "Фото отправлены!")


async def pinned_msg_button(call: CallbackQuery):
    forward = call.data.split("_")
    try:
        await bot.forward_message(call.message.chat.id, forward[2], int(forward[3]))
    except ApiTelegramException:
        try:
            await bot.send_message(call.message.chat.id, f"<b>Закреп от: {forward[4]}</b>")
            await bot.copy_message(call.message.chat.id, forward[2], int(forward[3]))
        except ApiTelegramException:
            await bot.answer_callback_query(call.id, "Сообщение не закреплено!")
            return
    await bot.answer_callback_query(call.id, "Закреп отправлен!")


def todict(obj):
    data = {}
    for key, value in obj.__dict__.items():
        try:
            data[key] = todict(value)
        except AttributeError:
            data[key] = value
    return data


async def transfer_to_target(msg: Message, data):
    target_id = data['state_data']

    reply = None
    if msg.reply_to_message is not None:
        reply = await BotDB.fetchone(
            "SELECT target_msg_id FROM chat_msgs WHERE chat_id = %s AND initiator_msg_id = %s",
            (msg.chat.id, msg.reply_to_message.id))

    try:
        copied_id = (await bot.copy_message(target_id, msg.chat.id, msg.id, reply_to_message_id=reply)).message_id
        await BotDB.execute("INSERT INTO chat_msgs (chat_id, initiator_msg_id, target_msg_id) VALUES (%s, %s, %s)",
                            (msg.chat.id, msg.id, copied_id))
    except ApiTelegramException as err:
        await bot.send_message(msg.chat.id, "<b>Этому человеку невозможно написать через Козловского.</b>"
                                            f"<i>({err.description})</i>")


async def transfer_to_initiator(msg: Message):
    initiator_chats = await BotDB.fetchall(
        "SELECT initiator, `current_user` FROM chats WHERE target = %s", msg.chat.id)

    for initiator_id, current_user in initiator_chats:
        if msg.chat.type != "private":
            if current_user != msg.from_user.id:
                await bot.send_message(initiator_id, f"<b>{user_link(msg.from_user, True)}</b>")
                await BotDB.execute("UPDATE chats SET `current_user` = %s WHERE initiator = %s",
                                    (msg.from_user.id, initiator_id))

        reply = None
        if msg.reply_to_message is not None:
            reply = await BotDB.fetchone(
                "SELECT initiator_msg_id FROM chat_msgs WHERE chat_id = %s AND target_msg_id = %s",
                (initiator_id, msg.reply_to_message.id))

        copied_id = (await bot.copy_message(initiator_id, msg.chat.id, msg.id, reply_to_message_id=reply)).message_id
        await BotDB.execute("INSERT INTO chat_msgs (chat_id, initiator_msg_id, target_msg_id) VALUES (%s, %s, %s)",
                            (initiator_id, copied_id, msg.id))


async def edit_msg_handler(msg: Message):
    state, target_id = await BotDB.get_state(msg.chat.id)
    initiator_chats = await BotDB.fetchall(
        "SELECT initiator, `current_user` FROM chats WHERE target = %s", msg.chat.id)

    if state == States.CHATTING:
        target_msg_id = await BotDB.fetchone(
            "SELECT target_msg_id FROM chat_msgs WHERE chat_id = %s AND initiator_msg_id = %s",
            (msg.chat.id, msg.id))
        await bot.edit_message_text(msg.text, target_id, target_msg_id)

    for initiator_id, current_user in initiator_chats:
        initiator_msg_id = await BotDB.fetchone(
            "SELECT initiator_msg_id FROM chat_msgs WHERE chat_id = %s AND target_msg_id = %s",
            (initiator_id, msg.id))
        await bot.edit_message_text(msg.text, initiator_id, initiator_msg_id)


async def delete_cmd_handler(msg: Message):
    try:
        reply = msg.reply_to_message.id

        state, target_id = await BotDB.get_state(msg.chat.id)
        initiator_chats = await BotDB.fetchall(
            "SELECT initiator, `current_user` FROM chats WHERE target = %s", msg.chat.id)

        if state == States.CHATTING:
            target_msg_id = await BotDB.fetchone(
                "SELECT target_msg_id FROM chat_msgs WHERE chat_id = %s AND initiator_msg_id = %s",
                (msg.chat.id, reply))
            await bot.delete_message(target_id, target_msg_id)

        for initiator_id, current_user in initiator_chats:
            initiator_msg_id = await BotDB.fetchone(
                "SELECT initiator_msg_id FROM chat_msgs WHERE chat_id = %s AND target_msg_id = %s",
                (initiator_id, reply))
            await bot.delete_message(initiator_id, initiator_msg_id)

        await bot.send_message(msg.chat.id, "<i>Сообщение удалено.</i>")
    except AttributeError:
        await bot.send_message(msg.chat.id, "Ответьте командой /delete на сообщение, которое требуется удалить.")
    except ApiTelegramException:
        await bot.send_message(msg.chat.id, "<i>Не удалось удалить сообщение.</i>")
    except ValueError:
        pass


async def end_chat(msg: Message):
    await BotDB.execute("DELETE FROM chats WHERE initiator = %s", msg.chat.id)
    await BotDB.set_state(msg.chat.id, -1)
    await bot.send_message(msg.chat.id, "Конец переписки", reply_markup=ReplyKeyboardRemove())


async def getting_id(msg: Message):
    markup = InlineKeyboardMarkup()
    if msg.content_type == 'contact':
        chat_id = msg.contact.user_id
        if not chat_id:
            await bot.send_message(msg.chat.id, "Этого человека нет в Telegram")
        else:
            markup.add(InlineKeyboardButton(text="Начать чат", callback_data=f"btn_chat_{chat_id}"))
            await bot.send_message(msg.chat.id, chat_id, reply_markup=markup)
    elif msg.forward_from is not None:
        chat_id = msg.forward_from.id
        markup.add(InlineKeyboardButton(text="Начать чат", callback_data=f"btn_chat_{chat_id}"))
        await bot.send_message(msg.chat.id, chat_id, reply_markup=markup)

    if msg.text == '/cancel':
        ContinueHandling()
    else:
        await BotDB.set_state(msg.chat.id, -1)
