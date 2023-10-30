import asyncio
from random import randint

import ujson
from telebot.types import Message, ReplyKeyboardMarkup

from helpers.bot import bot
from helpers.db import BotDB
from helpers.user_states import States


def get_main_keyboard(balance):
    return ReplyKeyboardMarkup(True).row(
        '🎲', '🎯', '🎳', '🏀', '⚽', '🎰').row(
        str(balance // 10), str(balance // 2), str(balance)).row(
        "💰 Баланс", "/cancel")


def calc_win_coefficient(emoji):
    if emoji in '🎲🎯🎳':
        return 6
    elif emoji in '🏀⚽':
        return 5
    else:
        return 64


@bot.message_handler(['casino'])
async def casino_cmd_handler(msg: Message):
    balance = await BotDB.get_balance(msg.chat.id)
    print(balance)

    bet = balance // 2
    await BotDB.set_state(msg.chat.id, States.CASINO, bet)
    await bot.send_message(msg.chat.id,
                           f"<b>🎰 КАЗИНО 🎰</b>\n\n"
                           f"Твой баланс: <b>{balance}</b>\n"
                           f"Текущая ставка: <b>{bet}</b>\n\n"
                           f"<i>⬇️ Используй кнопки внизу, чтобы взаимодействовать:</i>\n\n"
                           f"<b><i>1 строка:</i>\n"
                           f"Шансы выиграть:\n"
                           f"🎲, 🎯 и 🎳 - 1/6\n"
                           f"🏀 и ⚽ - 1/5\n"
                           f"🎰 - 1/64\n"
                           f"<i>2 строка:</i>\n"
                           f"Выбери ставку, также можно ввести свою в сообщении\n"
                           f"💰 Баланс - пополнить баланс\n"
                           f"/cancel - выход из казино</b>",
                           reply_markup=get_main_keyboard(balance))


@bot.message_handler(state=States.CASINO, content_types=['dice', 'text'])
async def casino_handler(msg: Message, data):
    balance = await BotDB.get_balance(msg.chat.id)
    bet = ujson.loads(data['state_data'])

    if msg.content_type == 'dice':
        dice, value = msg.dice.emoji, msg.dice.value
    elif msg.text[0] in ('🎲', '🎯', '🎳', '🏀', '⚽', '🎰'):
        dice, value = msg.text[0], randint(1, calc_win_coefficient(msg.text[0]))

    elif msg.text == '💰 Баланс':
        await bot.send_message(msg.chat.id,
                               f"Твой баланс: <b>{balance}\n\n"
                               f"Введи сумму, на которую хочешь пополнить баланс</b>\n\n"
                               f"<b>🎰 Казино</b> - вернуться в казино\n"
                               f"<b>/cancel</b> - выход из казино",
                               reply_markup=ReplyKeyboardMarkup(True).add("🎰 Казино", "/cancel"))
        await BotDB.set_state(msg.chat.id, States.BALANCE)
        return

    else:
        try:
            bet = int(msg.text)
            if bet < 1:
                await bot.send_message(msg.chat.id, "Ставка не может быть <b>меньше, чем 1</b>!")
            elif bet > balance:
                await bot.send_message(
                    msg.chat.id, f"Ставка не может быть <b>больше, чем твой баланс <i>({balance})</i></b>!")
            else:
                await bot.send_message(msg.chat.id, f"Новая ставка: <b>{bet}</b>")
                await BotDB.set_state(msg.chat.id, States.CASINO, bet)
        except ValueError:
            await bot.send_message(msg.chat.id, "Ставка может быть только <b>целым</b> числом!\n\n"
                                                "Чтобы <b>выйти</b> из режима казино, используй /cancel")
        return

    if balance <= 0:
        await bot.send_message(msg.chat.id, "<b>У тебя закончились деньги😢, пополни баланс</b>")
        return

    if msg.content_type == 'dice':
        await asyncio.sleep(2 if dice == '🎰' else 3)  # Задержка, т.к. бот спойлерит результат

    win_coefficient = calc_win_coefficient(dice)
    if win_coefficient / value < 2:
        win = bet * win_coefficient
        balance += win
        await bot.send_message(msg.chat.id, f"<b>🎉 ПОЗДРАВЛЯЕМ 🎉\n\n"
                                            f"Ты выиграл: <i>{win}</i>\n\n"
                                            f"Твой баланс: <i>{balance}</i></b>",
                               reply_markup=get_main_keyboard(balance))
    else:
        balance -= bet
        await bot.send_message(msg.chat.id, f"<b>😢 К сожалению, ты проиграл: <i>{bet}</i>\n\n"
                                            f"Твой баланс: <i>{balance}</i></b>",
                               reply_markup=get_main_keyboard(balance))
    await BotDB.execute("UPDATE `users` SET `balance` = %s WHERE `id` = %s;", (balance, msg.chat.id))


@bot.message_handler(state=States.BALANCE)
async def casino_balance_handler(msg: Message):
    balance = await BotDB.get_balance(msg.chat.id)

    if msg.text == '🎰 Казино':
        await bot.send_message(msg.chat.id, "<b>🎰 РЕЖИМ КАЗИНО 🎰</b>",
                               reply_markup=get_main_keyboard(balance))
        await BotDB.set_state(msg.chat.id, States.CASINO, balance // 2)
        return

    try:
        cash = int(msg.text)
        if cash < 1:
            await bot.send_message(msg.chat.id, "Баланс можно пополнить только на сумму <b>больше, чем 1</b>!")
        else:
            balance += cash
            await bot.send_message(msg.chat.id, f"<b>Баланс успешно пополнен на {cash}</b>!\n\n"
                                                f"Твой баланс: <b>{balance}</b>",
                                   reply_markup=get_main_keyboard(balance))

            await BotDB.execute("UPDATE `users` SET `balance` = %s WHERE `id` = %s;", (balance, msg.chat.id))
            await BotDB.set_state(msg.chat.id, States.CASINO, balance // 2)

    except ValueError:
        await bot.send_message(msg.chat.id, "Баланс можно пополнить только на <b>целую</b> сумму!")
