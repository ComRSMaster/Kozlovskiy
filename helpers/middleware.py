import time
from asyncio import ensure_future

from telebot.asyncio_handler_backends import BaseMiddleware
from telebot.asyncio_helper import ApiTelegramException
from telebot.types import Message
from telebot.util import content_type_media

from functions.chat_cmd import transfer_to_initiator
from helpers.bot import bot
from helpers.chat_update import new_private_cr, new_group_cr
from helpers.config import admin_chat
from helpers.db import BotDB
from helpers.utils import user_link


class ChatManagement(BaseMiddleware):
    def __init__(self):
        super().__init__()
        self.update_types = ['message']
        self.current_chat = 0

    async def pre_process(self, msg: Message, data):
        data['time'] = time.perf_counter()

        user_info = await BotDB.fetchone(
            "SELECT `log_msg`, `only_chess`, `state`, `state_data` FROM `users` WHERE `id` = %s", msg.chat.id)
        if user_info and not user_info[1]:
            msg.state = user_info[2]
            data['state_data'] = user_info[3]
            log_msg = user_info[0]
            data['new_user'] = False
        else:
            if msg.chat.type == "private":
                await new_private_cr(msg.chat)
            else:
                await new_group_cr(msg.chat)
            msg.state = -1
            log_msg = True
            data['new_user'] = True

        if log_msg and msg.content_type in content_type_media:  # log messages to admin
            if msg.chat.id + msg.from_user.id != self.current_chat:
                self.current_chat = msg.chat.id + msg.from_user.id
                if msg.chat.type == "private":
                    ensure_future(bot.send_message(
                        admin_chat, f"<b>{user_link(msg.from_user, True)}</b>"))
                else:
                    ensure_future(bot.send_message(
                        admin_chat, f"<b>{user_link(msg.from_user, True)}\n"
                                    f"{msg.chat.title} <code>{msg.chat.id}</code></b>"))
            try:
                ensure_future(bot.copy_message(admin_chat, msg.chat.id, msg.id))
            except ApiTelegramException:
                if msg.text:
                    ensure_future(bot.send_message(admin_chat, msg.text))
        await transfer_to_initiator(msg)

    async def post_process(self, message, data, exception):
        print('Время обработки:', time.perf_counter() - data['time'])
