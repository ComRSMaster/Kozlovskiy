import json
import random

from telebot.util import quick_markup

from helpers.bot import bot
from helpers.config import ends
from helpers.storage import users, save

with open('cities_easy.json', encoding="utf-8") as f:
    cities_easy = json.loads(f.read())

with open('cities_hard.json', encoding="utf-8") as f:
    cities_hard = json.loads(f.read())


def get_city_letter(str_city, i=-1):
    if str_city[i] in cities_easy:
        return str_city[i]
    return str_city[i - 1]


def city_game_handler(chat_id, user_city, args):
    if 'letter' in users[chat_id]:
        if 'complex_msg' in users[chat_id]:
            bot.edit_message_text(
                f"<b>Запущена игра в города.</b>\n<i>Начинай первым!</i>\n\n"
                f"Сложность: <b>{'ХАРДКОР' if users[chat_id]['complex'] == 'h' else 'ЛЕГКО'}</b>",
                chat_id, users[chat_id]['complex_msg'], parse_mode="HTML")
            users[chat_id].pop('complex_msg')
        if any(s in args for s in ends):
            users[chat_id].pop('letter')
            users[chat_id].pop('complex')
            users[chat_id].pop('complex_msg', 0)
            bot.send_message(chat_id, "<b>Конец игры</b>", "HTML")
            save()
            return True
        if user_city:
            letter = users[chat_id]['letter']
            if user_city[0] == letter or letter == '':
                try:
                    cities_db = cities_hard if users[chat_id]['complex'] == 'h' else cities_easy
                    random_city = random.choice(cities_db[get_city_letter(user_city)])
                    bot.send_message(chat_id, random_city)
                    users[chat_id]['letter'] = get_city_letter(random_city)
                    save()
                except KeyError:
                    bot.send_message(chat_id, "<b>Невозможно сгенерировать город</b>", "HTML")
            else:
                bot.send_message(chat_id, f"<b>Слово должно начинаться на букву:</b>  "
                                          f"<i>{letter.upper()}</i>", "HTML")
            return True
    elif "в города" in user_city:
        users[chat_id]['letter'] = ''
        users[chat_id]['complex'] = 'e'
        users[chat_id]['complex_msg'] = bot.send_message(
            chat_id, "<b>Запущена игра в города.</b>\n<i>Начинай первым!</i>\n\n"
                     "Сложность: <b>ЛЕГКО</b>\n⬇<i>Выбери сложность⬇</i>", "HTML",
            reply_markup=quick_markup({"ЛЕГКО👌": {'callback_data': 'btn_complex_e'},
                                       "🔥ХАРДКОР🔥": {'callback_data': 'btn_complex_h'}})).message_id
        save()
        return True
    return False


def inline_btn_complex_change(data, call):
    comp = data[-1:]
    bot.answer_callback_query(call.id, f"Выбрана сложность: {'ХАРДКОР' if comp == 'h' else 'ЛЕГКО'}")
    if users[str(call.message.chat.id)]['complex'] != comp:
        bot.edit_message_text(
            f"<b>Запущена игра в города.</b>\n<i>Начинай первым!</i>\n\n"
            f"Сложность: <b>{'ХАРДКОР' if comp == 'h' else 'ЛЕГКО'}</b>\n⬇<i>Выбери сложность⬇</i>",
            call.message.chat.id, users[str(call.message.chat.id)]['complex_msg'], parse_mode="HTML",
            reply_markup=quick_markup({"ЛЕГКО👌": {'callback_data': 'btn_complex_e'},
                                       "🔥ХАРДКОР🔥": {'callback_data': 'btn_complex_h'}}))
        users[str(call.message.chat.id)]['complex'] = comp
