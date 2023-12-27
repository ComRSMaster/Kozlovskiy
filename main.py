import ujson
from starlette.applications import Starlette
from starlette.responses import Response
from starlette.routing import Mount, Route, WebSocketRoute
from starlette.staticfiles import StaticFiles
from telebot.types import Update, Message, ReplyKeyboardRemove
from telebot.util import content_type_media

from functions import voice_msg
from functions.ai_talk import AiTalk
from functions.ai_upscale import register_ai_upscale_handler
from functions.books import register_books_handler
from functions.chat_cmd import register_chat_handler
from functions.chess import chess_mp_endpoint, get_chess_games
from functions.photo_desc import register_photo_desc_handler
from functions.simple_cmds import init_simple_commands
from functions.voice_msg import register_voice_msg_handler
from functions.casino import register_casino_handler
from functions.weather import register_weather_handler
from helpers import config, session_manager
from helpers.bot import bot
from helpers.db import BotDB
from helpers.gpts.gpts_apis import ChatGPT, GigaChat
from helpers.middleware import ChatManagement
from helpers.timer import timer

bot.setup_middleware(ChatManagement())


# from helpers.timer import timer


# @bot.message_handler(content_types=["user_shared"])
# def user_id_handler(msg: Message):
#     bot.send_message(msg.chat.id, msg.user_shared.user_id)
#
#
# @bot.message_handler(content_types=["chat_shared"])
# def chat_id_handler(msg: Message):
#     bot.send_message(msg.chat.id, msg.chat_shared.chat_id)
#

chatgpt = ChatGPT(config.openai_key)
gigachat = GigaChat(config.gigachat_secret)

init_simple_commands()
register_weather_handler()
register_voice_msg_handler()
register_photo_desc_handler()
register_ai_upscale_handler()
register_books_handler()
register_chat_handler()


@bot.message_handler(['cancel'], state='*')
async def command_cancel(msg: Message):
    await bot.send_message(msg.chat.id, "<b>Всё отменяю</b>", reply_markup=ReplyKeyboardRemove())
    await BotDB.set_state(msg.chat.id, -1)


register_casino_handler()
ai_talk_inst = AiTalk(chatgpt, gigachat)
bot.register_message_handler(ai_talk_inst.start_ai_talk_listener)


@bot.message_handler(content_types=content_type_media)
async def chatting(msg: Message):
    pass
    # if state == "wait_for_book_name":
    #     book_name_upload_state(msg)
    #     return
    # elif state == "wait_for_book" or state == "wait_for_done":
    #     book_upload_state(msg)
    #     return
    # elif state == "wait_for_pub":
    #     wait_user_upload_state(msg, state)
    #     return TODO


# @bot.callback_query_handler(None)
# def query(call: CallbackQuery):
#     elif data.startswith("btn_upload"):
#         book_upload_button(data, call)
#     elif data.startswith("btn_chat"):
#         start_chat(str(call.message.chat.id), data[data.rfind("_") + 1:])
#         bot.answer_callback_query(call.id, "Чат начат!")
#     elif data.startswith("btn_ignore"):
#         db.stats.ignore.append(int(data[data.rfind("_") + 1:]))
#         bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)



async def webhook_endpoint(request):
    await bot.process_new_updates([Update.de_json(ujson.loads(await request.body()))])
    return Response()


async def startup():
    if not config.is_dev:
        await bot.set_webhook(url=config.web_url + config.bot_token)
    print("server started")


async def shutdown():
    await bot.close_session()

    if BotDB.pool is not None:
        await BotDB.pool.clear()

    await session_manager.close_all_sessions()
    print("server stopped")


routes = [
    Route(f'/{config.bot_token}', webhook_endpoint, methods=['POST']),
    Route('/chess_games', get_chess_games, methods=['GET']),
    WebSocketRoute('/cmp', chess_mp_endpoint),  # chess multiplayer
    Mount('/', StaticFiles(directory='website', html=True))
]

app = Starlette(routes=routes, on_startup=[startup], on_shutdown=[shutdown])

# Запуск бота
if config.is_dev:
    BotDB.loop.create_task(bot.infinity_polling(skip_pending=True))

BotDB.loop.create_task(timer())
