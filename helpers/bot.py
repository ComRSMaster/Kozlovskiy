from io import StringIO

from telebot import asyncio_helper
from telebot.async_telebot import AsyncTeleBot, ExceptionHandler, asyncio_filters, logger

from helpers.config import bot_token, admin_chat, is_dev
from helpers.user_states import UserStateFilter


class ExcHandler(ExceptionHandler):
    def __init__(self):
        import logging
        self.log_stream = StringIO()
        logging.basicConfig(stream=self.log_stream, level=logging.WARNING)

    def handle(self, exception):
        logger.error(exception, exc_info=True)
        bot.send_message(admin_chat, f"ОШИБКА:\n{self.log_stream.getvalue()}"[:4096], '')
        self.log_stream.seek(0)
        self.log_stream.truncate(0)


if is_dev:
    logger.setLevel(10)


bot = AsyncTeleBot(bot_token, 'HTML',
                   exception_handler=None if is_dev else ExcHandler(), allow_sending_without_reply=True)
# if is_dev:
#     asyncio_helper.API_URL = 'https://api.telegram.org/bot{0}/test/{1}'
#     asyncio_helper.FILE_URL = 'https://api.telegram.org/file/bot{0}/test/{1}'
bot.add_custom_filter(asyncio_filters.TextMatchFilter())
bot.add_custom_filter(asyncio_filters.ChatFilter())
bot.add_custom_filter(asyncio_filters.IsReplyFilter())
bot.add_custom_filter(UserStateFilter())
