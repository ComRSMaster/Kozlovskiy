import requests
from telebot.apihelper import ApiTelegramException
from telebot.types import Message, ReplyKeyboardMarkup, KeyboardButton, ForceReply, ReplyKeyboardRemove
from telebot.util import quick_markup

from helpers.bot import bot
from helpers.config import weather_key
from helpers.storage import users, save

weather_msg_markup = quick_markup({"Другой город": {'callback_data': "btn_change_city"},
                                   "Обновить 🔄️": {'callback_data': "btn_update_weather"}})
select_private = ReplyKeyboardMarkup(True, input_field_placeholder="Введи город").add(
    KeyboardButton("Отправить своё местоположение", request_location=True))
select_public = ForceReply(input_field_placeholder="Введи город")
icon_to_emoji = {'01': "☀️", '02': "🌤", '03': "🌥", '04': "☁️", '09': "🌦️",
                 '10': "🌧", '11': "⛈", '13': "🌨️", '50': "🌫️"}


def weather_cmd_handler(msg: Message):
    user = users[str(msg.chat.id)]
    if 'lat' not in user:
        change_city_button(msg.chat.id, msg.chat.type)
        return
    bot.send_message(msg.chat.id, get_weather(user['lat'], user['lon']), 'HTML', reply_markup=weather_msg_markup)


def change_city_button(chat_id, chat_type):
    users[str(chat_id)]['s'] = "wait_for_city"
    bot.send_message(chat_id, "Введи свой город или отправь своё местоположение",
                     reply_markup=select_private if chat_type == 'private' else select_public)


def update_weather_button(call):
    user = users[str(call.message.chat.id)]
    try:
        bot.edit_message_text(get_weather(user['lat'], user['lon']), call.message.chat.id, call.message.message_id,
                              parse_mode='HTML', reply_markup=weather_msg_markup)
        bot.answer_callback_query(call.id, "Погода обновлена!")
    except ApiTelegramException:
        bot.answer_callback_query(call.id, "Ничего не изменилось")


def get_weather(lat, lon):
    weather = requests.get(
        f"https://api.openweathermap.org/data/2.5/weather?"
        f"lat={lat}&lon={lon}&appid={weather_key}&lang=ru&units=metric").json()
    name = weather['name'] if weather['name'] else f"Координаты: <i>{lat}, {lon}</i>"
    return f"<b>{name}:  <i>{weather['main']['temp']}°C\n" \
           f"{icon_to_emoji[weather['weather'][0]['icon'][:2]]} {weather['weather'][0]['description']}</i></b>\n" \
           f"Ощущается как:  <b><i>{weather['main']['feels_like']}°C</i></b>\n\n" \
           f"Давление:  <b><i>{weather['main']['pressure'] / 10}кПа</i></b>\n" \
           f"Влажность:  <b><i>{weather['main']['humidity']}%</i></b>"


def search_city(msg: Message):
    user = users[str(msg.chat.id)]
    if msg.content_type == 'location':
        user['lat'] = msg.location.latitude
        user['lon'] = msg.location.longitude
    elif msg.text:
        city_json = requests.get(
            f"http://api.openweathermap.org/geo/1.0/direct?q={msg.text}&limit=1&appid={weather_key}").json()
        if len(city_json) == 0:
            bot.send_message(msg.chat.id, "Город не найден. Введи свой город ещё раз.\n/cancel - отмена",
                             reply_markup=select_private if msg.chat.type == 'private' else select_public)
            return
        user['lat'] = city_json[0]['lat']
        user['lon'] = city_json[0]['lon']
    else:
        return
    user['s'] = ''
    bot.send_message(msg.chat.id, "Город успешно выбран!", reply_markup=ReplyKeyboardRemove())
    weather_cmd_handler(msg)
    save()
