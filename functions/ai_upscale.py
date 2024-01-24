import asyncio
from pprint import pprint

import aiohttp
import ujson
from telebot.asyncio_filters import TextFilter
from telebot.asyncio_helper import ApiTelegramException, logger
from telebot.types import Message, ForceReply, CallbackQuery
from telebot.util import content_type_media, extract_arguments, quick_markup

from helpers.bot import bot
from helpers.config import replicate_key
from helpers.db import BotDB
from helpers.long_texts import upscale_text
from helpers.session_manager import auto_close
from helpers.user_states import States
from helpers.utils import send_status_periodic, bool_emoji


session = auto_close(aiohttp.ClientSession(headers={
    "Authorization": f"Token {replicate_key}", "Content-Type": "application/json"
}, json_serialize=ujson.dumps))


def register_ai_upscale_handler():
    bot.register_message_handler(upscale_cmd_handler, commands=['up'])
    bot.register_message_handler(wait_photo_state, state=States.UP_PHOTO, content_types=['photo', 'document'])
    bot.register_callback_query_handler(inline_btn_upscale_settings, None,
                                        text=TextFilter(starts_with='btn_aiup'))


async def upscale_cmd_handler(msg: Message):
    file_id = None
    if msg.reply_to_message is not None:
        if msg.reply_to_message.content_type == "photo":
            file_id = msg.reply_to_message.photo[-1].file_id
        elif msg.reply_to_message.content_type == "document":
            file_id = msg.reply_to_message.document.file_id
    scale = extract_arguments(msg.text)
    if scale not in ['15', '25', '50']:
        scale = '15'
    if file_id is None:
        menu = await bot.send_message(msg.chat.id, upscale_text, reply_markup=gen_settings_markup(scale))

        await BotDB.set_state(msg.chat.id, States.UP_PHOTO, {'scale': scale, 'msg_id': menu.id})
    else:
        await image_upscale(msg.chat.id, file_id, scale, False)


async def wait_photo_state(msg: Message, data):
    if msg.content_type == "photo":
        file_id = msg.photo[-1].file_id
    else:
        file_id = msg.document.file_id

    state_data = ujson.loads(data['state_data'])
    await BotDB.set_state(msg.chat.id, -1)
    asyncio.ensure_future(bot.edit_message_reply_markup(msg.chat.id, state_data['msg_id']))
    await image_upscale(msg.chat.id, file_id, state_data['scale'])


async def image_upscale(chat_id, file_id, scale):
    loop = asyncio.get_event_loop()
    status_task = loop.create_task(send_status_periodic(chat_id, 'upload_document'))

    try:
        async with session.post('https://api.replicate.com/v1/predictions', json={
            "version": "660d922d33153019e8c263a3bba265de882e7f4f70396546b6c9c8f9d47a021a",
            "input": {"image": await bot.get_file_url(file_id), "noise": scale, 
                      "task_type": "Real-World Image Super-Resolution-Large"}}) as resp_raw:
            response = await resp_raw.json(loads=ujson.loads)
            if resp_raw.status != 201:
                logger.error(f'{resp_raw.status}\n{response}')
                return

        while response['status'] not in ["succeeded", "failed", "canceled"]:
            await asyncio.sleep(1)
            async with session.get(f"https://api.replicate.com/v1/predictions/{response['id']}") as resp_raw:
                response = await resp_raw.json(loads=ujson.loads)

        caption = f"Масштаб: <b>{scale}</b>"
        if response['status'] == "succeeded":
            try:
                async with session.head(response['output']) as size_resp:
                    if size_resp.content_length / 1024 / 1024 >= 20:  # if file size > 20mb
                        raise ValueError()

                await bot.send_document(chat_id, response['output'], caption=caption)
            except (ApiTelegramException, ValueError):
                await bot.send_message(chat_id, response['output'] + '\n\n' + caption)

        elif response['status'] == "canceled":
            await bot.send_message(chat_id, "<b>🛑 Команда отменена!</b>")

        elif response['error'].startswith("'NoneType'"):
            await bot.send_message(chat_id, "<b>❌ Тип файла не поддерживается...</b>")
        elif response['error'].startswith("CUDA out of memory"):
            await bot.send_message(chat_id, "<b>❌ Ошибка: фото слишком большое, попроуйте позже</b>")
        else:
            await bot.send_message(chat_id, f"<b>❌ Неизвестная ошибка... <pre>{response['error']}</pre></b>")
    finally:
        if status_task is not None:
            status_task.cancel()


async def inline_btn_upscale_settings(call: CallbackQuery):
    state, data = await BotDB.get_state(call.message.chat.id)

    if state != States.UP_PHOTO:
        await bot.answer_callback_query(call.id, 'Введите команду /up ещё раз', True)
        return

    scale = int(call.data[call.data.rfind('_') + 1:])
    if data['scale'] == scale:
        return
    data['scale'] = scale

    try:
        await bot.edit_message_reply_markup(call.message.chat.id, call.message.id,
                                            reply_markup=gen_settings_markup(data['scale']))
    except ApiTelegramException:
        pass

    await BotDB.set_state(call.message.chat.id, States.UP_PHOTO, data)


def gen_settings_markup(scale):
    settings_markup = {(i + (' ✅' if i == scale else '')): {'callback_data': f'btn_aiup_scale_{i}'} for i in ['15', '25', '50']}

    return quick_markup(settings_markup, row_width=3)

# async def image_upscale(self, chat_id, file_id):
#     loop = asyncio.get_event_loop()
#     task = loop.create_task(send_status_periodic(chat_id, 'upload_document'))
#
#     async with self.session.post('/api/torch-srgan', headers={
#         'api-key': generate_tryit(USER_AGENT),
#         'user-agent': USER_AGENT
#     }, data={
#         'image': await bot.get_file_url(file_id)
#     }) as resp_raw:
#         print(resp_raw.status)
#         response = await resp_raw.json(loads=ujson.loads)
#         print(response)
#
#         try:
#             await bot.send_document(chat_id, response['output_url'])
#         except ApiTelegramException as e:
#             logger.error(e)
#             await bot.send_message(chat_id, response['output_url'])
#     task.cancel()
