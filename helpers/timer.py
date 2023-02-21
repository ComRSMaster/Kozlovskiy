import sys
import time
from datetime import datetime

from functions.ai_talk import ai_talk
from helpers.config import MIN_BIRTHDAY_HOUR, success_vid, admin_chat
from helpers.storage import users, save
from helpers.bot import bot
from helpers.update_chat import update_user_info

if sys.version_info < (3, 9):
    # noinspection PyUnresolvedReferences,PyPackageRequirements
    from backports.zoneinfo import ZoneInfo
else:
    from zoneinfo import ZoneInfo


def timer_step():
    now = datetime.now(ZoneInfo("Europe/Moscow"))
    for u in users:
        update_user_info(bot.get_chat(u))
        birthday: str = users[u].get("birthday")
        if birthday is None:
            continue
        day, month = birthday.split("/")
        if MIN_BIRTHDAY_HOUR <= now.hour and now.day == int(day) and now.month == int(month):
            if users[u].get("congratulated", 0):
                continue
            bot.send_video(u, success_vid, caption="<b>Поздравляю тебя с днём рождения!</b>🎉🎉🎉",
                           parse_mode="HTML")
            bot.send_message(admin_chat, "Я поздравил с ДР: " + u)
            users[u]["congratulated"] = 1
            ai_talk("У меня сегодня день рождения!", u, start="Поздравляю тебя с днём рождения!🎉🎉🎉", append=True)
        else:
            users[u].pop("congratulated", 0)
    save()


def timer():
    while True:
        timer_step()
        time.sleep(3000)
