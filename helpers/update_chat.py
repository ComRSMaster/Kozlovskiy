from os.path import isfile

from functions.ai_talk import ai_talk
from helpers.bot import bot
from helpers.config import success_vid, admin_chat
from helpers.long_texts import help_text
from helpers.storage import users, save, ignore, chat_id_my, chat_id_pen
from telebot.types import Chat, InlineKeyboardMarkup, InlineKeyboardButton, Message, ChatMemberUpdated

from helpers.utils import n


def setup_bot_handlers():
    @bot.message_handler(content_types=["new_chat_title"])
    def new_chat_title(msg: Message):
        users[str(msg.chat.id)]['name'] = msg.new_chat_title
        save()

    @bot.message_handler(content_types=["new_chat_photo"])
    def new_chat_photo(msg: Message):
        users[str(msg.chat.id)]['photo_id'] = msg.new_chat_photo[0].file_unique_id
        with open(f'website/p/{msg.new_chat_photo[0].file_unique_id}.jpg', 'wb') as file:
            file.write(bot.download_file(bot.get_file(msg.new_chat_photo[0].file_id).file_path))
        save()

    @bot.message_handler(content_types=["delete_chat_photo"])
    def delete_chat_photo(msg: Message):
        users[str(msg.chat.id)]['photo_id'] = None
        save()

    @bot.message_handler(content_types=["group_chat_created", "supergroup_chat_created", "channel_chat_created"])
    def new_chat_created(msg: Message):
        new_group_cr(msg.chat)

    @bot.my_chat_member_handler(None)
    def ban_handler(member: ChatMemberUpdated):
        if member.new_chat_member.status in ["restricted", "kicked", "left"]:
            users.pop(str(member.chat.id))
            try:
                ignore.remove(str(member.chat.id))
            except ValueError:
                pass
            save()
            bot.send_message(admin_chat, "<b>Удалён чат:  <pre>" + str(member.chat.id) + "</pre></b>", "HTML")
        elif member.chat.type != "private":
            new_group_cr(member.chat)


def migrate_to_chat_id(msg: Message):
    users[str(msg.migrate_to_chat_id)] = users.pop(str(msg.chat.id))
    try:
        ignore[ignore.index(str(msg.chat.id))] = str(msg.migrate_to_chat_id)
    except ValueError:
        pass
    try:
        chat_id_my[chat_id_my.index(str(msg.chat.id))] = str(msg.migrate_to_chat_id)
    except ValueError:
        pass
    try:
        chat_id_pen[chat_id_pen.index(str(msg.chat.id))] = str(msg.migrate_to_chat_id)
    except ValueError:
        pass
    save()


def update_user_info(chat: Chat):
    chat_id = str(chat.id)
    users[chat_id]['private'] = chat.type == "private"
    users[chat_id]['name'] = chat.title if not chat.type == "private" else chat.first_name + n(chat.last_name, " ")
    users[chat_id]['desc'] = n(chat.bio) if chat.type == "private" else n(chat.description)
    if chat.photo is None:
        users[chat_id]['photo_id'] = None
    else:
        file_name = chat.photo.small_file_unique_id + ".jpg"
        if not isfile(f'website/p/{file_name}') or chat.photo.small_file_unique_id != users[chat_id].get('photo_id'):
            with open(f'website/p/{file_name}', 'wb') as file:
                file.write(bot.download_file(bot.get_file(chat.photo.small_file_id).file_path))
        users[chat_id]['photo_id'] = chat.photo.small_file_unique_id


def new_group_cr(chat: Chat):
    chat_id = str(chat.id)
    if users.get(chat_id) is not None:
        return
    users[chat_id] = {'s': '', 'balance': 1000}
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text="Ignore", callback_data="btn_ignore_" + chat_id))
    bot.send_message(admin_chat, "<b>Новая группа: " + chat.title + "  <pre>" +
                     chat_id + "</pre></b>", 'HTML', reply_markup=markup)
    update_user_info(bot.get_chat(chat.id))
    save()


def new_private_cr(chat: Chat):
    chat_id = str(chat.id)
    users[chat_id] = {'s': '', 'balance': 1000}
    bot.send_message(chat_id, help_text, 'HTML')
    bot.send_video(chat_id, success_vid, caption="<b>Чем я могу помочь?</b>🤔", parse_mode="HTML")
    ai_talk("/start", str(chat.id), start="Чем я могу помочь?🤔")
    update_user_info(bot.get_chat(chat.id))
    save()
