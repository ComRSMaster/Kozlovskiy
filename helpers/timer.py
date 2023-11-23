import asyncio
import sys
from datetime import datetime

from telebot.asyncio_helper import ApiTelegramException

from helpers.config import MIN_BIRTHDAY_HOUR, success_vid, admin_chat
from helpers.db import BotDB
from helpers.bot import bot
from helpers.chat_update import update_user_info, delete_chat
from helpers.user_states import States

if sys.version_info < (3, 9):
    # noinspection PyUnresolvedReferences,PyPackageRequirements
    from backports.zoneinfo import ZoneInfo
else:
    from zoneinfo import ZoneInfo


async def timer_step():
    now = datetime.now(ZoneInfo("Europe/Moscow"))
    for chat_id, birth_day, birth_month, is_greeted, state in await BotDB.fetchall(
            "SELECT `id`, `birth_day`, `birth_month`, `is_greeted`, `state` FROM `users` WHERE `only_chess` = 0"):
        try:
            await update_user_info(await bot.get_chat(chat_id))
        except ApiTelegramException as e:
            if 'chat not found' in e.description:
                pass
            else:
                raise e
                # await delete_chat(chat_id)

        if birth_day is None:
            continue

        if MIN_BIRTHDAY_HOUR <= now.hour and now.day == birth_day and now.month == birth_month:
            if is_greeted:
                continue
            await bot.send_video(chat_id, success_vid, caption="<b>Поздравляю тебя с днём рождения!</b>🎉🎉🎉")
            birthday_dialog = [
                {"role": "user",
                 "content": "У меня сегодня день рождения!"},
                {"role": "assistant",
                 "content": "Поздравляю тебя с днём рождения!🎉🎉🎉"}
            ]
            if state == -1:
                await BotDB.set_state(chat_id, States.AI_TALK,
                                      {'reply': False, 'model': 0, 'messages': birthday_dialog})
            elif state == States.AI_TALK:
                _, data = await BotDB.get_state(chat_id)
                data['messages'].extend(birthday_dialog)
                await BotDB.set_state(chat_id, state, data)

            await BotDB.execute("UPDATE `users` SET `is_greeted` = 1 WHERE `id` = %s", chat_id)
            await bot.send_message(admin_chat, f"Я поздравил с ДР: {chat_id}")
        elif is_greeted:
            await BotDB.execute("UPDATE `users` SET `is_greeted` = DEFAULT WHERE `id` = %s", chat_id)
        await asyncio.sleep(0.2)


async def timer():
    while True:
        await timer_step()
        await asyncio.sleep(3000)
