from io import StringIO

from telebot import ExceptionHandler, apihelper, logger, TeleBot
from telebot.types import Update

from helpers.config import bot_token, admin_chat, is_dev, web_url


class ExcHandler(ExceptionHandler):
    def __init__(self):
        import logging
        self.log_stream = StringIO()
        logging.basicConfig(stream=self.log_stream, level=logging.WARNING)

    def handle(self, exception):
        logger.error(exception, exc_info=True)
        bot.send_message(admin_chat, f"ОШИБКА:\n{self.log_stream.getvalue()}"[:4096])
        self.log_stream.seek(0)
        self.log_stream.truncate(0)


apihelper.ENABLE_MIDDLEWARE = True
bot = TeleBot(bot_token, exception_handler=None if is_dev else ExcHandler(), allow_sending_without_reply=True)


def start_bot():
    print("bot started")
    if is_dev:
        bot.infinity_polling(skip_pending=True)
    else:
        from helpers import webserver

        bot.set_webhook(url=web_url + bot_token)
        webserver.parse_updates = lambda json_string: bot.process_new_updates(
            [Update.de_json(json_string)])
        webserver.run_webserver()

        bot.remove_webhook()
