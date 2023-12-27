import asyncio
import re
from asyncio import ensure_future, Task
from random import choice
from typing import Union

import ujson
from telebot.asyncio_filters import TextFilter
from telebot.asyncio_helper import ApiTelegramException, logger
from telebot.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, CallbackQuery
from telebot.util import content_type_media, quick_markup

from functions.voice_msg import stt, get_voice_id
from helpers.bot import bot
from helpers.config import random_ans, calls, calls_private, bot_token
from helpers.db import BotDB
from helpers.gpts.gpts_apis import ChatGPT, GigaChat
from helpers.user_states import States
from helpers.utils import bool_emoji, send_status_periodic, nlp_stop

# talks: dict[int, list] = {}
# reply_markups: dict[int, InlineKeyboardMarkup] = {}
# chat = HuggingChat({'hf-chat': hugging_cookie})
MODELS = ['🤖 ChatGPT 3.5', '💪 GigaChat', '🔮 Магический шар']


def get_stop_markup(task_id):
    return quick_markup({'🛑 Стоп': {'callback_data': f'ai_stop_{task_id}'}})


class AiTalk:
    def __init__(self, chatgpt: ChatGPT, gigachat: GigaChat):
        self.chatgpt = chatgpt
        self.gigachat = gigachat
        self.generating_tasks: dict[str, Task] = {}
        bot.register_message_handler(command_cancel, commands=['cancel'], state=States.AI_TALK)
        bot.register_message_handler(self.ai_talk_handler, state=States.AI_TALK, content_types=content_type_media)
        bot.register_callback_query_handler(self.inline_btn_stop, None, text=TextFilter(starts_with='ai_stop'))
        bot.register_callback_query_handler(self.inline_btn_stop, None, text=TextFilter(starts_with='ai_stop'))

    async def get_ai_response(self, provider: Union[ChatGPT, GigaChat], messages: list, chat_id: int,
                              reply_id: int = None):
        loop = asyncio.get_event_loop()

        print(messages)

        async def generating_task():

            msg_id = None
            status_task = None
            all_result = ''
            curr_result = ''

            try:
                async for text in provider.chat(messages, cooldown=35):  # 35 токенов за сообщение
                    # print(text)
                    if len(curr_result + text) > 4096:
                        # await bot.edit_message_reply_markup(chat_id, msg_id)
                        msg_id = None
                        curr_result = text
                    else:
                        curr_result += text
                        all_result += text

                    async def send_to_user(use_md=True):
                        nonlocal msg_id, status_task
                        if msg_id is None:
                            msg_id = (await bot.send_message(
                                chat_id, curr_result, 'Markdown' if use_md else 'Text', reply_to_message_id=reply_id,
                                reply_markup=stop_markup)).id
                            if status_task is None:
                                status_task = loop.create_task(send_status_periodic(chat_id, 'typing'))
                        else:
                            # print(curr_result, chat_id, msg_id)
                            await bot.edit_message_text(curr_result, chat_id, msg_id,
                                                        parse_mode='Markdown' if use_md else 'Text',
                                                        reply_markup=stop_markup)

                    try:
                        await send_to_user()
                    except ApiTelegramException as e:
                        logger.error(e)
                        await send_to_user(False)
                        continue
            except asyncio.CancelledError:
                print('STOP')
                return all_result
            finally:
                if status_task is not None:
                    status_task.cancel()
            ensure_future(bot.edit_message_reply_markup(chat_id, msg_id))
            return all_result

        gen_task = loop.create_task(generating_task())
        self.generating_tasks[gen_task.get_name()] = gen_task

        stop_markup = get_stop_markup(gen_task.get_name())

        result = await gen_task

        return result

    async def ai_talk_handler(self, msg: Message, data):
        state_data = ujson.loads(data['state_data'])
        is_reply, model, messages = state_data['reply'], state_data['model'], state_data['messages']
        show_reply = None if msg.chat.type == 'private' else False

        if msg.content_type == 'text':
            keyboard_btn_clicked = False

            if msg.text.startswith("↩ Только ответы"):
                state_data['reply'] = not is_reply
                if is_reply:
                    await bot.send_message(msg.chat.id, '<b>Теперь бот будет отвечать на все сообщения подряд</b>',
                                           reply_markup=gen_init_markup(False, model))
                else:
                    await bot.send_message(msg.chat.id,
                                           '<b>Теперь бот будет отвечать только на ↩ ответы на сообщения</b>',
                                           reply_markup=gen_init_markup(True, model))
                keyboard_btn_clicked = True

            elif msg.text in MODELS:
                state_data['model'] = MODELS.index(msg.text)

                if state_data['model'] == 2:  # magic ball
                    text = f'Выбран режим: <b>{msg.text}</b>'
                else:
                    text = f'Выбрана нейросеть: <b>{msg.text}</b>'

                await bot.send_message(
                    msg.chat.id, text,
                    reply_markup=gen_init_markup(state_data['reply'] or show_reply, state_data['model']))
                keyboard_btn_clicked = True

            if keyboard_btn_clicked:
                await BotDB.set_state(msg.chat.id, States.AI_TALK, state_data)
                return

        voice_id = get_voice_id(msg, False)
        user_msg = await get_user_message(msg, voice_id)
        if user_msg is None:
            return

        if nlp_stop(user_msg):
            await BotDB.set_state(msg.chat.id, -1)

            await bot.send_message(msg.chat.id, "Пока👋", reply_markup=ReplyKeyboardRemove())

            return

        if model != 2:  # save messages
            state_data['messages'].append({
                "role": "user",
                "content": user_msg
            })
            await BotDB.set_state(msg.chat.id, States.AI_TALK, state_data)

        if is_reply:
            if msg.reply_to_message is None or msg.reply_to_message.from_user.id != int(bot_token.split(':')[0]):
                return
            else:
                reply_id = msg.id
        else:
            reply_id = None

        if model == 2:  # magic ball
            await bot.send_message(msg.chat.id, choice(random_ans), reply_to_message_id=reply_id)
            return
        else:  # chatgpt or gigachat
            ensure_future(bot.send_chat_action(msg.chat.id, 'typing'))
            answer = await self.get_ai_response(
                self.chatgpt if model == 0 else self.gigachat, messages, msg.chat.id, reply_id)

        print(answer)

        state_data['messages'].append({
            "role": "assistant",
            "content": answer
        })

        # if voice_id:
        #     await bot.send_voice(msg.chat.id, await tts(answer))

        await BotDB.set_state_safe(msg.chat.id, States.AI_TALK, state_data)

    async def start_ai_talk_listener(self, msg: Message):
        if msg.content_type != 'text':
            return

        is_private = msg.chat.type == 'private'
        args = re.split(r'[ ,.;&!?\[\]]+', msg.text.lower(), maxsplit=3)
        if any(s in args for s in calls) or (is_private and any(s in args for s in calls_private)):
            # reply_markups[msg.chat.id] = markup
            # init_id = (await bot.send_message(msg.chat.id, '...', reply_markup=markup)).id
            # conv_id = await chat.new_conversation()

            # await BotDB.set_state(msg.chat.id, States.CHATTING,
            #                       {'reply': is_reply, 'mode': 'ai', 'init_id': init_id, 'conv_id': conv_id})
            # await get_ai_response(msg.text, msg.chat.id, init_id, True, conv_id)

            ensure_future(bot.send_message(msg.chat.id, f'Текущая нейросеть: <b>{MODELS[1]}</b>',
                                           disable_notification=True,
                                           reply_markup=gen_init_markup(not is_private or None, 1)))
            data = {'reply': False, 'model': 1, 'messages': [{
                "role": "user",
                "content": msg.text
            }]}
            ensure_future(bot.send_chat_action(msg.chat.id, 'typing'))

            await BotDB.set_state(msg.chat.id, States.AI_TALK, data)
            answer = await self.get_ai_response(
                self.gigachat, data['messages'], msg.chat.id, None if is_private else msg.id)

            data['messages'].append({
                "role": "assistant",
                "content": answer
            })
            await BotDB.set_state_safe(msg.chat.id, States.AI_TALK, data)

    async def inline_btn_stop(self, call: CallbackQuery):
        task_id = call.data[8:]
        if task_id in self.generating_tasks:
            self.generating_tasks[task_id].cancel()
        try:
            await bot.edit_message_reply_markup(call.message.chat.id, call.message.id)
        except ApiTelegramException:
            pass

    # async def stupid_ai_response(self, messages):
    #     talk = [m['content'] for m in messages]
    #     async with self.stupid_ai_session.post('https://api.aicloud.sbercloud.ru/public/v2/boltalka/predict',
    #                                            json={"instances": [{"contexts": [talk]}]}) as response:
    #         res = await response.json(loads=ujson.loads)
    #     return str(res["responses"][2:-2]).replace("%bot_name", random.choice(["Даня", "Козловский"]))


def gen_init_markup(reply, model_index):
    markup = ReplyKeyboardMarkup(True)
    if reply is not None:
        markup.row(KeyboardButton(f'↩ Только ответы {bool_emoji(reply)}'))
    return markup.row(
        *[KeyboardButton(name) for index, name in enumerate(MODELS) if index != model_index])


async def get_user_message(msg: Message, voice_id):
    if msg.content_type == 'text':
        return msg.text
    if msg.content_type == 'sticker':
        return msg.sticker.emoji
    if voice_id is not None:
        ensure_future(bot.send_chat_action(msg.chat.id, "typing"))
        return await stt(voice_id, False)
    if msg.caption is not None:
        return msg.caption

async def command_cancel(msg: Message):
    await bot.send_message(msg.chat.id, "Пока👋", reply_markup=ReplyKeyboardRemove())
    await BotDB.set_state(msg.chat.id, -1)


# def append_to_talk(chat_id: int, user_msg: str, ai_msg: str):
#     data = ujson.loads(msg.state_data)
#     talk = data['talk']
#
#     if States.CHATTING in states:
#         talk = states[States.CHATTING]
#         talk.append(user_msg)
#         talk.append(ai_msg)
#     else:
#         states[States.CHATTING] = [user_msg, ai_msg]

# def gen_init_markup(reply, magic_ball):
#     values = {} if reply is None else {f'{bool_emoji(reply)} Только ответы': {'callback_data': 'btn_aitalk_reply'}}
#     values[f'{bool_emoji(magic_ball)} Магический шар'] = {'callback_data': 'btn_aitalk_mode'}
#
#     return quick_markup(values, 1)

#
#
# @bot.callback_query_handler(None, text=TextFilter(starts_with='btn_aitalk'))
# async def inline_btn_upscale_settings(call: CallbackQuery):
#     state, data = await BotDB.get_state(call.message.chat.id)
#
#     if state != States.CHATTING:
#         await bot.answer_callback_query(call.id, 'Запустите разговор с ИИ ещё раз', True)
#         return
#
#     if call.data[11:].startswith('reply'):
#         data['reply'] = not data['reply']
#     else:  # is magic ball?
#         data['mode'] = 'magic_ball' if data['mode'] == 'ai' else 'ai'
#
#     await BotDB.set_state(call.message.chat.id, States.CHATTING, data)
#
#     try:
#         markup = gen_init_markup(None if call.message.chat.type == 'private' else data['reply'], data['mode'] != 'ai')
#         reply_markups[call.message.chat.id] = markup
#         await bot.edit_message_reply_markup(call.message.chat.id, call.message.id, reply_markup=markup)
#     except ApiTelegramException:
#         pass
