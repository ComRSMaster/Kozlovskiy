import aiohttp
from bs4 import BeautifulSoup
from telebot.types import Message

from helpers import session_manager
from helpers.bot import bot
from helpers.session_manager import auto_close

session = auto_close(aiohttp.ClientSession())


def register_photo_desc_handler():
    bot.register_message_handler(what_cmd_handler, commands=['what'])


async def what_cmd_handler(msg: Message):
    if msg.reply_to_message is not None:
        msg = msg.reply_to_message
    if msg.content_type != 'photo':
        await bot.send_message(msg.chat.id, "<b>Ответьте этой командой на уже отправленное фото</b>")
        return

    await bot.send_chat_action(msg.chat.id, action='typing')
    url_pic = f"https://yandex.ru/images/search?rpt=imageview&url={await bot.get_file_url(msg.photo[-1].file_id)}"

    async with session.get(url_pic) as response:
        results = BeautifulSoup(
            await response.text(), 'lxml').find(
            'section', 'CbirTags').find_all('a')

    await bot.reply_to(msg, '\n'.join(f"• {res.find('span').get_text().capitalize()}" for res in results))
