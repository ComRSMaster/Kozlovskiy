import aiohttp
import ujson
from telebot.asyncio_filters import TextFilter
from telebot.asyncio_helper import ApiTelegramException
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, ForceReply, Message, CallbackQuery, ReplyKeyboardRemove
from telebot.util import quick_markup

from helpers.bot import bot
from helpers.config import weather_key
from helpers.db import BotDB
from helpers.session_manager import auto_close
from helpers.user_states import States

weather_msg_markup = quick_markup({"Другой город": {'callback_data': "btn_change_city"},
                                   "Обновить 🔄️": {'callback_data': "btn_update_weather"}})
select_private = ReplyKeyboardMarkup(True, input_field_placeholder="Введи город").add(
    KeyboardButton("Отправить своё местоположение", request_location=True))
select_public = ForceReply(input_field_placeholder="Введи город")
weather_icons = {'01': "☀️", '02': "🌤", '03': "🌥", '04': "☁️", '09': "🌦️",
                 '10': "🌧", '11': "⛈", '13': "🌨️", '50': "🌫️"}

weather_session = auto_close(
    aiohttp.ClientSession('https://api.openweathermap.org', json_serialize=ujson.dumps))


def register_weather_handler():
    bot.register_message_handler(weather_cmd_handler, commands=['weather'])
    bot.register_message_handler(search_city, state=States.WAIT_GEO, content_types=['text', 'location'])
    bot.register_callback_query_handler(change_city_button, None, text=TextFilter('btn_change_city'))
    bot.register_callback_query_handler(update_weather_button, None, text=TextFilter('btn_update_weather'))


async def weather_cmd_handler(msg: Message):
    lat, lon = await BotDB.get_coord(msg.chat.id)

    if not lat:
        await change_city(msg.chat.id, msg.chat.type)
        return

    await bot.send_message(msg.chat.id, await get_weather(lat, lon), reply_markup=weather_msg_markup)


async def change_city_button(call: CallbackQuery):
    await bot.answer_callback_query(call.id, "Введи свой город")
    await change_city(call.message.chat.id, call.message.chat.type)


async def update_weather_button(call: CallbackQuery):
    lat, lon = await BotDB.get_coord(call.message.chat.id)

    try:
        await bot.edit_message_text(await get_weather(lat, lon), call.message.chat.id,
                                    call.message.message_id, reply_markup=weather_msg_markup)
        await bot.answer_callback_query(call.id, "Погода обновлена!")

    except ApiTelegramException:
        await bot.answer_callback_query(call.id, "Ничего не изменилось")


async def change_city(chat_id, chat_type):
    await bot.send_message(chat_id, "Введи свой город или отправь своё местоположение",
                           reply_markup=select_private if chat_type == 'private' else select_public)
    await BotDB.set_state(chat_id, States.WAIT_GEO)


async def get_weather(lat, lon):
    async with weather_session.get(
            '/data/2.5/weather', params={
                'lat': lat, 'lon': lon, 'appid': weather_key, 'lang': 'ru', 'units': 'metric'}) as resp_raw:
        weather = await resp_raw.json(loads=ujson.loads)

        city = weather['name'] if weather['name'] else f"Координаты: <i>{lat}, {lon}</i>"
        return \
            f"<b>{city}:  <i>{weather['main']['temp']}°C\n" \
            f"{weather_icons[weather['weather'][0]['icon'][:2]]} {weather['weather'][0]['description']}</i></b>\n" \
            f"Ощущается как:  <b><i>{weather['main']['feels_like']}°C</i></b>\n\n" \
            f"Давление:  <b><i>{weather['main']['pressure'] / 10}кПа</i></b>\n" \
            f"Влажность:  <b><i>{weather['main']['humidity']}%</i></b>"


async def search_city(msg: Message):
    if msg.content_type == 'location':
        lat = msg.location.latitude
        lon = msg.location.longitude
    else:
        async with weather_session.get(
                '/geo/1.0/direct', params={
                    'q': msg.text, 'limit': 1, 'appid': weather_key}) as resp_raw:
            city_json = await resp_raw.json(loads=ujson.loads)

            if len(city_json) == 0:
                await bot.send_message(msg.chat.id,
                                       "<b>Город не найден. Введи свой город ещё раз.</b>\n/cancel - отмена",
                                       reply_markup=select_private if msg.chat.type == 'private' else select_public)
                return
            lat = city_json[0]['lat']
            lon = city_json[0]['lon']

    await bot.send_message(msg.chat.id, "<b>Город успешно выбран!</b>", reply_markup=ReplyKeyboardRemove())
    await BotDB.execute("UPDATE `users` SET `coord` = POINT(%s, %s), `state` = -1 WHERE `id` = %s",
                        (lat, lon, msg.chat.id))
    await weather_cmd_handler(msg)
