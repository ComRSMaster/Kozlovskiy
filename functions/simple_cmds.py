import os
import re
import sys
from asyncio import sleep
from io import StringIO
from random import randint, choice

from telebot.asyncio_helper import ApiTelegramException
from telebot.types import Message, ReplyKeyboardRemove

from functions.ai_talk import gen_init_markup
from helpers.bot import bot
from helpers.config import admin_chat
from helpers.db import BotDB
from helpers.long_texts import help_text
from helpers.user_states import States


def init_simple_commands():
    @bot.message_handler(['start'])
    async def command_start(msg: Message, data):
        start_msg = "О чём поговорим?🤔"
        if data['new_user']:
            start_msg = "Чем я могу помочь?🤔"
        else:
            await bot.send_message(msg.chat.id, start_msg, reply_markup=gen_init_markup(
                None if msg.chat.type == 'private' else False, 1))
        await BotDB.set_state(msg.chat.id, States.AI_TALK,
                              {'reply': False, 'model': 1, 'messages': [
                                  {"role": "user",
                                   "content": "Привет"},
                                  {"role": "assistant",
                                   "content": start_msg}
                              ]})

    @bot.message_handler(['help'])
    async def command_help(msg: Message):
        await bot.send_message(msg.chat.id, help_text)

    @bot.message_handler(['id'])
    async def command_id(msg: Message):
        await BotDB.set_state(msg.chat.id, States.GETTING_ID)
        await bot.send_message(msg.chat.id, "Теперь перешли мне любое сообщение из чата, "
                                            "или поделись со мной контактом этого человека.\n /cancel - отмена")

    @bot.message_handler(['rnd'])
    async def command_rnd(msg: Message):
        nums = re.findall(r'\d+', msg.text)
        start_num = 1 if len(nums) < 2 else int(nums[0])
        end_num = 6 if len(nums) == 0 else int(nums[0]) if len(nums) == 1 else int(nums[1])
        if start_num > end_num:
            start_num, end_num = end_num, start_num

        await bot.send_message(
            msg.chat.id,
            f"🎲 Случайное число <b>от</b> <code>{start_num}</code> <b>до</b> <code>{end_num}</code>:\n"
            f"<pre>{randint(start_num, end_num)}</pre>")

    @bot.message_handler(['cancel'], state=-1)
    async def command_cancel(msg: Message):
        await bot.send_message(msg.chat.id, "<b>Я совершенно свободен</b>", reply_markup=ReplyKeyboardRemove())

    @bot.message_handler(content_types=['poll'])
    async def voter(msg: Message):
        await bot.reply_to(msg, choice(msg.poll.options).text)

    # admin only commands
    @bot.message_handler(['kill_bot'], chat_id=[admin_chat])
    async def command_kill_bot(msg: Message):
        await bot.remove_webhook()
        await bot.send_message(msg.chat.id, "Бот успешно отключен")
        print("bot killed")
        # noinspection PyProtectedMember
        os._exit(0)

    @bot.message_handler(['exec'], chat_id=[admin_chat])
    async def command_exec(msg: Message):
        code_out = StringIO()
        sys.stdout = code_out
        try:
            exec(msg.text[6:])
        except Exception as e:
            await bot.send_message(msg.chat.id, f"ОШИБКА: {e}"[:4096], '')
            return
        finally:
            sys.stdout = sys.__stdout__
        o = code_out.getvalue()
        if o == '':
            o = "Ничего не выведено"
        await bot.send_message(msg.chat.id, o)

    @bot.message_handler(['broadcast'], chat_id=[admin_chat], is_reply=True)
    async def command_broadcast(msg: Message):
        # TODO test
        for user_id, in await BotDB.fetchall("SELECT `id` FROM `users` WHERE `is_private` = 1 AND `only_chess` = 0"):
            for _ in range(5):
                try:
                    await bot.copy_message(user_id, msg.chat.id, msg.reply_to_message.id)
                    break
                except ApiTelegramException as ex:
                    if ex.error_code == 429:
                        await sleep(ex.result_json['parameters']['retry_after'])
                    else:
                        raise
