import asyncio
import re

import aiohttp
import ujson
from telebot.types import Message

from helpers.bot import bot
from helpers.config import assemblyai_key
from helpers.session_manager import auto_close

RE_EMOJI = re.compile("["
                      u"\U0001F600-\U0001F64F"  # emoticons
                      u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                      u"\U0001F680-\U0001F6FF"  # transport & map symbols
                      u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                      u"\U00002702-\U000027B0"
                      u"\U000024C2-\U0001F251"
                      "]+", flags=re.UNICODE)

assemblyai_session = auto_close(
    aiohttp.ClientSession('https://api.assemblyai.com', json_serialize=ujson.dumps))
# tts_session = auto_close(aiohttp.ClientSession('https://api.voicerss.org'))


def register_voice_msg_handler():
    bot.register_message_handler(decode_cmd_handler, commands=['d'])


async def decode_cmd_handler(msg: Message):
    file_id = get_voice_id(msg, True)
    if file_id is None:
        await bot.send_message(msg.chat.id,
                               "<b>Ответьте на голосовое/видео сообщение командой /d, чтобы его расшифровать.</b>"
                               "\n<i>Если вы сделали всё правильно и видите это сообщение, "
                               "то перешлите сюда это голосовое</i>")
    else:
        progress_id = (await bot.reply_to(msg.reply_to_message, "Расшифровка...")).id

        await bot.edit_message_text(await stt(file_id, True), msg.reply_to_message.chat.id, progress_id)


def get_voice_id(msg: Message, reply: bool):
    if reply:
        if msg.reply_to_message is None:
            return None
        msg = msg.reply_to_message
    file_id = None
    if msg.content_type == "voice":
        file_id = msg.voice.file_id
    elif msg.content_type == "audio":
        file_id = msg.audio.file_id
    elif msg.content_type == "video_note":
        file_id = msg.video_note.file_id
    elif msg.content_type == "video":
        file_id = msg.video.file_id
    return file_id


async def stt(file_id: str, stats):
    headers = {"authorization": assemblyai_key}

    async with assemblyai_session.post('/v2/transcript',
                                       json={"audio_url": await bot.get_file_url(file_id), "language_code": 'ru'},
                                       headers=headers) as response:
        transcript_id = (await response.json(loads=ujson.loads))['id']

    while True:
        async with assemblyai_session.get(f'/v2/transcript/{transcript_id}',
                                          headers=headers) as result_raw:
            result = await result_raw.json(loads=ujson.loads)
            print(result)

        if result['status'] == 'completed':
            text = result['text']
            break

        elif result['status'] == 'error':
            text = f"❌ Возникла ошибка: {result['error']}" if stats else "Скажи что-нибудь"
            break

        await asyncio.sleep(2)

    if not text:
        text = "Тут ничего нет🤔" if stats else "Скажи что-нибудь"

    print(text)
    return text

# async def tts(text: str):
#     async with tts_session.post(
#             f"/?key={tts_key}&hl=ru-RU&v=Peter&r=2&f=24khz_16bit_mono&"
#             f"src={RE_EMOJI.sub(r'', text)}") as response:
#         pcm = await response.read()
#
#         opus_encoder = OpusEncoder()
#         opus_encoder.set_application("voip")
#         opus_encoder.set_sampling_frequency(24000)
#         opus_encoder.set_channels(1)
#
#         return opus_encoder.encode(pcm)
