from os.path import isfile

from helpers.bot import bot
from helpers.config import success_vid, admin_chat
from helpers.db import BotDB
from telebot.types import Chat, InlineKeyboardMarkup, InlineKeyboardButton, Message, ChatMemberUpdated

from helpers.utils import n


@bot.message_handler(content_types=["new_chat_title"])
async def new_chat_title(msg: Message):
    await BotDB.execute("UPDATE `users` SET `name` = %s WHERE `id` = %s", (msg.new_chat_title, msg.chat.id))


@bot.message_handler(content_types=["new_chat_photo"])
async def new_chat_photo(msg: Message):
    await BotDB.execute("UPDATE `users` SET `photo_id` = %s WHERE `id` = %s",
                        (msg.new_chat_photo[0].file_unique_id, msg.chat.id))

    with open(f'website/p/{msg.new_chat_photo[0].file_unique_id}.jpg', 'wb') as file:
        file.write(await bot.download_file(await bot.get_file(msg.new_chat_photo[0].file_id).file_path))


@bot.message_handler(content_types=["delete_chat_photo"])
async def delete_chat_photo(msg: Message):
    await BotDB.execute("UPDATE `users` SET `photo_id` = NULL WHERE `id` = %s", msg.chat.id)


@bot.message_handler(content_types=["group_chat_created", "supergroup_chat_created", "channel_chat_created"])
async def new_chat_created(msg: Message):
    await new_group_cr(msg.chat)


@bot.message_handler(content_types=["migrate_to_chat_id"])
async def migrate_to_chat_id(msg: Message):
    await BotDB.execute("UPDATE `users` SET `id` = %s WHERE `id` = %s", (msg.migrate_to_chat_id, msg.chat.id))


@bot.my_chat_member_handler(None)
async def ban_handler(member: ChatMemberUpdated):
    if member.new_chat_member.status in ["restricted", "kicked", "left"]:
        await delete_chat(member.chat.id)


async def delete_chat(chat_id):
    await BotDB.execute("DELETE FROM `users` WHERE `id` = %s", chat_id)
    await bot.send_message(admin_chat, f"<b>Удалён чат:  <code>{chat_id}</code></b>")


async def update_user_info(chat: Chat):
    name = chat.title if not chat.type == "private" else chat.first_name + n(chat.last_name, " ")
    desc = chat.bio if chat.type == "private" else chat.description
    if chat.photo:
        photo_id = chat.photo.small_file_unique_id
        file_name = f'website/p/{photo_id}.jpg'
        if not isfile(file_name):
            with open(file_name, 'wb') as file:
                file.write(await bot.download_file((await bot.get_file(chat.photo.small_file_id)).file_path))
    else:
        photo_id = None
    await BotDB.execute("UPDATE `users` SET `name` = %s, `desc` = %s, `photo_id` = %s WHERE `id` = %s",
                        (name, desc, photo_id, chat.id))


async def new_group_cr(chat: Chat):
    await BotDB.new_user(chat.id, chat.title, chat.description, False)
    await update_user_info(await bot.get_chat(chat.id))

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Ignore", callback_data=f"btn_ignore_{chat.id}"))
    await bot.send_message(admin_chat,
                           f"<b>Новая группа: {chat.title}  <code>{chat.id}</code></b>", reply_markup=markup)


async def new_private_cr(chat: Chat):
    await bot.send_video(chat.id, success_vid, caption="<b>Чем я могу помочь?</b>🤔")
    await BotDB.new_user(chat.id, chat.first_name + n(chat.last_name, " "), chat.bio, True)
    await update_user_info(await bot.get_chat(chat.id))

    await bot.send_message(admin_chat, f"<b>Новый пользователь: {chat.first_name}  <code>{chat.id}</code></b>")
