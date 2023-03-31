import random
import time

from telebot.types import Message, ReplyKeyboardMarkup

from helpers.bot import bot
from helpers.storage import users, save


def gen_main_keyboard(balance):
    return ReplyKeyboardMarkup(True).add(
        '🎲', '🎯', '🎳', '🏀', '⚽', '🎰', row_width=6).add(
        str(balance // 10), str(balance // 2), str(balance)).add(
        "💰 Баланс", "/cancel")


def calc_win_coefficient(emoji):
    if emoji in '🎲🎯🎳':
        return 6
    elif emoji in '🏀⚽':
        return 5
    else:
        return 64


def casino_cmd_handler(msg: Message):
    user = users[str(msg.chat.id)]
    balance = user['balance']
    user['s'] = 'casino'
    user['bet'] = balance // 2
    bot.send_message(msg.chat.id,
                     f"<b>🎰 КАЗИНО 🎰</b>\n\n"
                     f"Твой баланс: <b>{balance}</b>\n"
                     f"Текущая ставка: <b>{user['bet']}</b>\n\n"
                     f"<i>⬇️ Используй кнопки внизу, чтобы взаимодействовать:</i>\n\n"
                     f"<b><i>1 строка:</i>\n"
                     f"Шансы выиграть:\n"
                     f"🎲, 🎯 и 🎳 - 1/6\n"
                     f"🏀 и ⚽ - 1/5\n"
                     f"🎰 - 1/64\n"
                     f"<i>2 строка:</i>\n"
                     f"Выбери ставку, также можно ввести свою в сообщении\n"
                     f"💰 Баланс - пополнить баланс\n"
                     f"/cancel - выход из казино</b>", 'HTML',
                     reply_markup=gen_main_keyboard(balance))
    save()


def casino_handler(msg: Message):
    user = users[str(msg.chat.id)]
    if msg.content_type == 'dice':
        if user['balance'] == 0:
            bot.send_message(msg.chat.id, "<b>У тебя закончились деньги😢, пополни баланс</b>", 'HTML')
            return
        time.sleep(2 if msg.dice.emoji == '🎰' else 3)  # задержка, т.к. бот предсказывает результат
        if random.randint(1, 40) == 1:
            lose = user['balance']
            user['balance'] = 0
            bot.send_message(msg.chat.id, f"<b>😢 К сожалению, ты проиграл: <i>{lose}</i>!\n\n"
                                          f"Твой баланс: <i>{user['balance']}</i></b>", 'HTML',
                             reply_markup=gen_main_keyboard(user['balance']))
            bot.send_message(msg.chat.id, "<b>У тебя закончились деньги😢, пополни баланс</b>", 'HTML')
        else:
            win = user['bet'] * calc_win_coefficient(msg.dice.emoji)
            user['balance'] += win
            bot.send_message(msg.chat.id, f"<b>🎉 ПОЗДРАВЛЯЕМ 🎉\n\n"
                                          f"Ты выиграл: <i>{win}</i>!\n\n"
                                          f"Твой баланс: <i>{user['balance']}</i></b>", 'HTML',
                             reply_markup=gen_main_keyboard(user['balance']))
        save()

    elif msg.text == '💰 Баланс':
        bot.send_message(msg.chat.id,
                         f"Твой баланс: <b>{user['balance']}\n\n"
                         f"Введи сумму, на которую хочешь пополнить баланс</b>\n\n"
                         f"<b>🎰 Казино</b> - вернуться в казино\n"
                         f"<b>/cancel</b> - выход из казино", 'HTML',
                         reply_markup=ReplyKeyboardMarkup(True).add("🎰 Казино", "/cancel"))
        user['s'] = 'balance'
        save()
    elif msg.text == '🎰 Казино':
        bot.send_message(msg.chat.id, "<b>🎰 РЕЖИМ КАЗИНО 🎰</b>", 'HTML',
                         reply_markup=gen_main_keyboard(user['balance']))
        user['s'] = 'casino'
        save()
    else:
        try:
            bet = int(msg.text)

            if bet < 1:
                bot.send_message(msg.chat.id, "Ставка не может быть <b>меньше, чем 1</b>!", 'HTML')
            elif bet > user['balance']:
                bot.send_message(
                    msg.chat.id,
                    f"Ставка не может быть <b>больше, чем твой баланс <i>({user['balance']})</i></b>!", 'HTML')
            else:
                user['bet'] = bet
                bot.send_message(msg.chat.id, f"Новая ставка: <b>{bet}</b>", 'HTML')
                save()
        except ValueError:
            bot.send_message(msg.chat.id, "Ставка может быть только <b>целым</b> числом!\n\n"
                                          "Чтобы <b>выйти</b> из режима казино, используй /cancel", 'HTML')


def casino_balance_handler(msg: Message):
    try:
        balance = int(msg.text)
        if balance < 1:
            bot.send_message(msg.chat.id, "Баланс можно пополнить только на сумму <b>больше, чем 1</b>!", 'HTML')
        else:
            user = users[str(msg.chat.id)]
            user['balance'] += balance
            bot.send_message(msg.chat.id, f"<b>Баланс успешно пополнен на {balance}</b>!\n\n"
                                          f"Твой баланс: <b>{user['balance']}</b>", 'HTML',
                             reply_markup=gen_main_keyboard(user['balance']))
            user['s'] = 'casino'
            save()
    except ValueError:
        bot.send_message(msg.chat.id, "Баланс можно пополнить только на <b>целую</b> сумму!", 'HTML')
