from asyncio import ensure_future
from random import choice

import ujson
from telebot.asyncio_filters import TextFilter
from telebot.types import Message, CallbackQuery
from telebot.util import quick_markup

from helpers.bot import bot
from helpers.config import ends
from helpers.long_texts import get_cities_text
from helpers.db import BotDB
from helpers.user_states import States
from helpers.utils import nlp_stop

with open('cities_easy.json', encoding="utf-8") as f:
    cities_easy = ujson.load(f)

with open('cities_hard.json', encoding="utf-8") as f:
    cities_hard = ujson.load(f)

comp_markup = quick_markup({"ЛЕГКО👌": {'callback_data': 'btn_complex_e'},
                            "🔥ХАРДКОР🔥": {'callback_data': 'btn_complex_h'}})


def complex_name(comp):
    return 'ХАРДКОР' if comp == 'h' else 'ЛЕГКО'


def get_city_letter(city, i=-1):
    if len(city) < -i:
        return False
    if city[i].lower() in cities_easy:
        return city[i].lower()
    return get_city_letter(city, i - 1)


@bot.message_handler(['cities'])
async def cities_cmd(msg: Message):
    await BotDB.set_state(msg.chat.id, States.CITIES, {
        'complex_msg': (await bot.send_message(
            msg.chat.id, f"{get_cities_text('ЛЕГКО')}\n⬇ <i>Выбери сложность</i> ⬇",
            reply_markup=comp_markup)).id,
        'letter': '', 'complex': 'e'})


@bot.message_handler(state=States.CITIES)
async def cities_game_handler(msg: Message, data):
    state_data = ujson.loads(data['state_data'])

    if 'complex_msg' in state_data:
        ensure_future(bot.edit_message_text(
            get_cities_text(complex_name(state_data['complex'])), msg.chat.id, state_data.pop('complex_msg')))
        await BotDB.set_state(msg.chat.id, States.CITIES, state_data)

    if nlp_stop(msg.text):
        await bot.send_message(msg.chat.id, "<b>Конец игры</b>")
        await BotDB.set_state(msg.chat.id, -1)
        return

    letter = state_data['letter']
    if msg.text[0].lower() != letter and letter != '':
        await bot.send_message(msg.chat.id, f"<b>Город должен начинаться на букву:</b>  <i>{letter.upper()}</i>")
        return

    cities_db = cities_hard if state_data['complex'] == 'h' else cities_easy

    user_letter = get_city_letter(msg.text)
    if not user_letter:
        await bot.send_message(msg.chat.id, '<b>Невозможно сгенерировать такой город</b>')
        return

    random_city = choice(cities_db[user_letter])
    await bot.send_message(msg.chat.id, random_city)

    state_data['letter'] = get_city_letter(random_city)
    await BotDB.set_state(msg.chat.id, States.CITIES, state_data)


@bot.callback_query_handler(None, text=TextFilter(starts_with='btn_complex'))
async def inline_btn_complex_change(call: CallbackQuery):
    state, data = await BotDB.get_state(call.message.chat.id)
    if state != States.CITIES:
        await bot.answer_callback_query(call.id, 'Запусти игру в города ещё раз!', True)
        return

    new_comp = call.data[-1:]  # Новая сложность
    comp_text = complex_name(new_comp)
    await bot.answer_callback_query(call.id, f"Выбрана сложность: {comp_text}")

    if data['complex'] != new_comp:
        await bot.edit_message_text(
            f"{get_cities_text(comp_text)}\n⬇ <i>Выбери сложность</i> ⬇",
            call.message.chat.id, data['complex_msg'], reply_markup=comp_markup)
        data['complex'] = new_comp

        await BotDB.set_state(call.message.chat.id, States.CITIES, data)
