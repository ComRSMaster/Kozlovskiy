import configparser
import json
import os
import random
import re
import time
from datetime import datetime
from threading import Thread
from zoneinfo import ZoneInfo

import requests
import telebot
from bs4 import BeautifulSoup

import webserver


class ExceptionHandler(telebot.ExceptionHandler):
    def handle(self, exception):
        if "Bot token is not defined" in exception.args[0]:
            print("Неправильный токен бота")
            # noinspection PyProtectedMember
            os._exit(0)


content_types = ["text", "audio", "document", "photo", "sticker", "video", "video_note", "voice", "location", "contact",
                 "new_chat_title", "group_chat_created", "supergroup_chat_created", "channel_chat_created",
                 "migrate_to_chat_id", "poll"]
admin_chat = "-1001624831175"
config = configparser.ConfigParser()
config.read("config.ini", encoding="utf8")  # читаем конфиг
TOKEN = os.getenv("Kozlovskiy_token")
bot = telebot.TeleBot(TOKEN, exception_handler=ExceptionHandler())
MIN_IGNORE_TIME = 80000
MAX_IGNORE_TIME = 700000
MIN_ALLOWED_HOUR = 12
MAX_ALLOWED_HOUR = 21


def update_groups(load=False):
    global groups
    global groups_str
    with open("groups.txt", "r+", encoding="utf-8") as groups_file:
        if load:
            groups = [chat.split(':  ') for chat in groups_file.readlines()]
        else:
            groups_file.truncate()
            groups_file.writelines(str(x) + ':  ' + str(y) for x, y in groups)
    groups_str = ''.join('<pre>' + str(x) + '</pre>:  <b>' + str(y) + '</b>' for x, y in groups)


def save():
    config.set('Settings', 'ignore', json.dumps(ignore))
    config.set('Settings', 'images', json.dumps(images))
    config.set('Dump', 'current_chat', current_chat)
    config.set('Dump', 'current_user', current_user)
    config.set('Dump', 'auto_start', json.dumps(auto_start))
    config.set('Dump', 'users', json.dumps(users))
    config.set('Dump', 'active_chats', json.dumps(active_chats))
    config.set('Dump', 'active_goroda', json.dumps(active_goroda))
    config.set('Dump', 'current_letters', json.dumps(current_letters, ensure_ascii=False))
    config.set('Dump', 'wait_for_chat_id', json.dumps(wait_for_chat_id))
    config.set('Dump', 'chat_id_my', json.dumps(chat_id_my))
    config.set('Dump', 'chat_id_pen', json.dumps(chat_id_pen))
    config.set('Dump', 'chat_msg_my', json.dumps(chat_msg_my))
    config.set('Dump', 'chat_msg_pen', json.dumps(chat_msg_pen))
    config.set('Dump', 'current_users', json.dumps(current_users))
    config.set('Dump', 'ai_datas', json.dumps(ai_datas, ensure_ascii=False))
    with open('config.ini', 'w', encoding="utf-8") as file:
        config.write(file)


groups = []
groups_str = ""
update_groups(True)

ignore = json.loads(config["Settings"]['ignore'])
ans = json.loads(config["Settings"]['ans'])
ans_voice = json.loads(config["Settings"]['ans_voice'])
images: dict = json.loads(config["Settings"]['images'])
starts = json.loads(config["Settings"]['starts'])
calls = json.loads(config["Settings"]['calls'])
calls_private = json.loads(config["Settings"]['calls_private'])
ends = json.loads(config["Settings"]['ends'])
searches = json.loads(config["Settings"]['searches'])
randoms = json.loads(config["Settings"]['randoms'])
current_chat = config["Dump"]['current_chat']
current_user = config["Dump"]['current_user']
auto_start: dict = json.loads(config["Dump"]['auto_start'])
users = json.loads(config["Dump"]['users'])
active_chats: list = json.loads(config["Dump"]['active_chats'])
active_goroda: list = json.loads(config["Dump"]['active_goroda'])
current_letters = json.loads(config["Dump"]['current_letters'])
wait_for_chat_id = json.loads(config["Dump"]['wait_for_chat_id'])
chat_id_my = json.loads(config["Dump"]['chat_id_my'])
chat_id_pen = json.loads(config["Dump"]['chat_id_pen'])
chat_msg_my = json.loads(config["Dump"]['chat_msg_my'])
chat_msg_pen = json.loads(config["Dump"]['chat_msg_pen'])
current_users = json.loads(config["Dump"]['current_users'])
ai_datas = json.loads(config["Dump"]['ai_datas'])

with open('cities.json', encoding="utf-8") as f:
    goroda = json.loads(f.read())


def get_id(message):
    wait_for_chat_id.append(str(message.chat.id))
    bot.send_message(message.chat.id,
                     "Теперь перешли мне любое сообщение из чата, "
                     "или поделись со мной контактом этого человека.\n /cancel - отмена")
    save()


def start_chat(chat_id, chat):
    try:
        if chat == chat_id:
            bot.send_message(chat_id, "<b>Нельзя писать самому себе через Козловского.</b>", 'HTML')
            return
        if chat_id in chat_id_my:
            bot.send_message(chat_id, "<b>Вы уже пишете кому-то через Козловского.\n"
                                      "Чтобы законичить, введите /cancel</b>", 'HTML')
            return
        chat_info = bot.get_chat(chat)
        markup = telebot.types.InlineKeyboardMarkup()
        if chat_info.photo is not None:
            markup.add(telebot.types.InlineKeyboardButton(text="Посмотреть фото профиля",
                                                          callback_data="btn_photo_" + chat_info.photo.big_file_id))
        if chat_info.pinned_message is not None:
            markup.add(telebot.types.InlineKeyboardButton(
                text="Посмотреть закреп", callback_data=f"btn_pinned_{chat_info.pinned_message.chat.id}_"
                                                        f"{chat_info.pinned_message.message_id}_"
                                                        f"{chat_info.pinned_message.from_user.first_name}"))
        bot.send_message(chat_id, parse_chat(chat_info) + "\n<b>/cancel - закончить переписку\n"
                                                          "/delete - удалить сообщение у собеседника</b>", 'HTML',
                         reply_markup=markup)
        chat_id_my.append(chat_id)
        chat_id_pen.append(chat)
        current_users.append("")
        chat_msg_my.append([])
        chat_msg_pen.append([])
        save()
    except telebot.apihelper.ApiTelegramException:
        bot.send_message(chat_id, "Неправильный chat_id")


def get_city_letter(str_city, i=-1):
    if str_city[i] in goroda:
        return str_city[i]
    return str_city[i - 1]


def set_next_time(chat_id: str):
    auto_start[chat_id] = datetime.now(ZoneInfo("Europe/Moscow")).timestamp() + \
                          random.randint(MIN_IGNORE_TIME, MAX_IGNORE_TIME)


def ai_talk(chat_id: str, msg_text, args, is_private=True, auto_answer=""):
    try:
        index = active_chats.index(chat_id)
        if any(s in args for s in ends):
            active_chats.pop(index)
            ai_datas.pop(index)
            bot.send_message(chat_id, "Пока")
            save()
            return
        if msg_text != "":
            bot.send_chat_action(chat_id, action="typing")
            ai_datas[index]["instances"][0]["contexts"][0].append(msg_text)
            if auto_answer == "":
                res = requests.post('https://api.aicloud.sbercloud.ru/public/v2/boltalka/predict',
                                    json=ai_datas[index]).json()
                answer = str(res["responses"][2:-2]).replace("%bot_name", random.choice(["Даня", "Козловский"]))
            else:
                answer = auto_answer
            set_next_time(chat_id)
            bot.send_message(chat_id, answer, disable_notification=auto_answer != "")
            ai_datas[index]["instances"][0]["contexts"][0].append(answer)
            save()
    except ValueError:
        if any(s in args for s in calls) or (is_private and any(s in args for s in calls_private)):
            active_chats.append(str(chat_id))
            ai_datas.append({"instances": [{"contexts": [[]]}]})
            ai_talk(chat_id, msg_text, args, is_private, auto_answer)
            save()


def photo_search(chat_id, search_photo):
    bot.send_chat_action(chat_id, action="typing")
    url_pic = "https://yandex.ru/images/search?rpt=imageview&url=https://api.telegram.org/file/bot" + \
              TOKEN + "/" + bot.get_file(search_photo.file_id).file_path
    soup = BeautifulSoup(requests.get(url_pic).text, 'lxml')
    results_vk = soup.find('div', class_='CbirSites-ItemInfo')
    if 'vk.com/id' in results_vk.find('a').get('href'):
        bot.send_message(chat_id, results_vk.find('div', class_='CbirSites-ItemDescription').get_text())
        return
    results = soup.find('section', 'CbirTags').find_all('a')
    bot.send_message(chat_id, results[0].find('span').get_text() + ", " + results[1].find('span').get_text())


def todict(obj):
    data = {}
    for key, value in obj.__dict__.items():
        try:
            data[key] = todict(value)
        except AttributeError:
            data[key] = value
    return data


def n(text, addition=''):
    """Если text - None, то вернуть пустую строку"""
    return "" if text is None else addition + text


def parse_chat(chat: telebot.types.Chat):
    text = "<b>Начат чат с:</b>\n\n"
    if chat.type == "private":
        text += 'Человек<b><a href="tg://user?id=' + str(chat.id) + '">: ' + chat.first_name + \
                n(chat.last_name, ' ') + '</a></b>' + n(chat.bio, '\nОписание: ') + n(chat.username, '\n@')
    elif chat.type == "channel":
        return str(todict(chat))
    else:
        text += "Группа: " + chat.title + n(chat.description, '\nОписание: ') + \
                n(chat.username, '\n@') + n(chat.invite_link, '\nСсылка: ')
    return text


@bot.message_handler(content_types=content_types)
def chatting(msg: telebot.types.Message):
    global current_chat
    global current_user

    current = str(n(msg.text) + n(msg.caption)).lower()
    args = re.split(r'[ ,.;&!?\[\]]+', current)
    # chat management
    if msg.chat.type == "private":
        if str(msg.chat.id) not in users:
            users.append(str(msg.chat.id))
            set_next_time(str(msg.chat.id))
            save()
    else:
        new_group = False
        if msg.content_type in ["group_chat_created", "supergroup_chat_created", "channel_chat_created"]:
            new_group = True
        else:
            for g in groups:
                if g[0] == str(msg.chat.id):
                    break
            else:
                new_group = True
        if new_group:
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(
                telebot.types.InlineKeyboardButton(text="Ignore", callback_data="btn_ignore_" + str(msg.chat.id)))
            bot.send_message(admin_chat,
                             "<b>Новая группа: " + msg.chat.title + "  <pre>" + str(msg.chat.id) + "</pre></b>",
                             'HTML', reply_markup=markup)
            groups.append([str(msg.chat.id), msg.chat.title + '\n'])
            update_groups()
            return
    if msg.content_type == "new_chat_title":
        for g in groups:
            if g[0] == str(msg.chat.id):
                g[1] = msg.chat.title + '\n'
                break
        update_groups()
        return
    elif msg.content_type == "migrate_to_chat_id":
        for g in groups:
            if g[0] == str(msg.chat.id):
                g[0] = str(msg.migrate_to_chat_id)
                break
        update_groups()
        try:
            ignore[ignore.index(str(msg.chat.id))] = str(msg.migrate_to_chat_id)
        except ValueError:
            pass
        try:
            chat_id_my[chat_id_my.index(str(msg.chat.id))] = str(msg.migrate_to_chat_id)
        except ValueError:
            pass
        try:
            chat_id_pen[chat_id_pen.index(str(msg.chat.id))] = str(msg.migrate_to_chat_id)
        except ValueError:
            pass
        save()
        return
    # stats
    elif str(msg.chat.id) not in ignore:
        if str(msg.chat.id) != current_chat or str(msg.from_user.id) != current_user:
            current_chat = str(msg.chat.id)
            current_user = str(msg.from_user.id)
            save()
            if msg.chat.type == "private":
                bot.send_message(admin_chat, "<b>" +
                                 str(msg.chat.first_name) + " " + str(msg.chat.id) + "</b>", 'HTML')
            else:
                bot.send_message(admin_chat, "<b>" +
                                 str(msg.from_user.first_name) + " " + str(msg.from_user.id) + "\n " +
                                 str(msg.chat.title) + " " + str(msg.chat.id) + "</b>", 'HTML')
        bot.copy_message(admin_chat, msg.chat.id, msg.id)

    # voter
    if msg.content_type == "poll":
        bot.send_message(msg.chat.id, random.choice(msg.poll.options).text, reply_to_message_id=msg.id)

    # cancel
    elif current.startswith("/cancel"):
        try:
            wait_for_chat_id.remove(str(msg.chat.id))
            bot.send_message(msg.chat.id, "Всё отменяю")
            save()
        except ValueError:
            try:
                my_index = chat_id_my.index(str(msg.chat.id))
                chat_id_my.pop(my_index)
                chat_id_pen.pop(my_index)
                chat_msg_my.pop(my_index)
                chat_msg_pen.pop(my_index)
                current_users.pop(my_index)
                bot.send_message(msg.chat.id, "Конец переписки")
                save()
            except ValueError:
                bot.send_message(msg.chat.id, "Я совершенно свободен")

    # chat228
    if str(msg.chat.id) in wait_for_chat_id:
        markup = telebot.types.InlineKeyboardMarkup()
        if msg.content_type == 'contact':
            user_id = str(msg.contact.user_id)
            if user_id == "None":
                bot.send_message(msg.chat.id, "Этого человека нет в Telegram.")
            else:
                markup.add(telebot.types.InlineKeyboardButton(text="Начать чат",
                                                              callback_data="btn_chat_" + user_id))
                bot.send_message(msg.chat.id, user_id, reply_markup=markup)
        else:
            try:
                chat_id = str(msg.forward_from.id)
                markup.add(telebot.types.InlineKeyboardButton(text="Начать чат",
                                                              callback_data="btn_chat_" + chat_id))
                bot.send_message(msg.chat.id, chat_id, reply_markup=markup)
            except AttributeError:
                bot.send_message(msg.chat.id, "Вы не переслали сообщение.")
        wait_for_chat_id.remove(str(msg.chat.id))
        save()
    try:
        other_index = chat_id_pen.index(str(msg.chat.id))  # собеседник
        if msg.chat.type != "private":
            if str(msg.from_user.id) not in current_users[other_index]:
                current_users[other_index] = str(msg.from_user.id)
                bot.send_message(chat_id_my[other_index], "<b>" + str(msg.from_user.first_name) + " <pre>" + str(
                    msg.from_user.id) + "</pre></b>", 'HTML')
        reply = None
        try:
            reply = chat_msg_my[other_index][chat_msg_pen[other_index].index(msg.reply_to_message.message_id)]
        except AttributeError:
            pass
        chat_msg_my[other_index].append(
            bot.copy_message(chat_id_my[other_index], msg.chat.id, msg.id, reply_to_message_id=reply).message_id)
        chat_msg_pen[other_index].append(msg.id)
        save()
    except ValueError:
        pass

    # ignore
    if current.startswith("/ignore"):
        if msg.chat.type != "private":
            bot.send_message(msg.chat.id, "<i>Эту команду можно использовать только в лс</i>", 'HTML')
            return
        try:
            auto_start.pop(str(msg.chat.id))
            bot.send_message(msg.chat.id, "<b>Теперь Козловский не будет начинать переписку сам.</b>\n"
                                          "<i>Чтобы вернуть всё как было, введите /ignore ещё раз.</i>", 'HTML')
        except KeyError:
            set_next_time(str(msg.chat.id))
            bot.send_message(msg.chat.id, "<b>Теперь Козловский сможет начать переписку сам</b>", 'HTML')
        save()
        return

    # delete
    elif current.startswith("/delete"):
        try:
            reply = msg.reply_to_message.message_id
            my_index = chat_id_my.index(str(msg.chat.id))
            bot.delete_message(chat_id_pen[my_index], chat_msg_pen[my_index][chat_msg_my[my_index].index(reply)])
            bot.send_message(msg.chat.id, "<i>Сообщение удалено.</i>", 'HTML')
        except AttributeError:
            bot.send_message(msg.chat.id, "Ответьте командой /delete на сообщение, которое требуется удалить.")
        except telebot.apihelper.ApiTelegramException:
            bot.send_message(msg.chat.id, "<i>Не удалось удалить сообщение.</i>", 'HTML')
        except ValueError:
            pass
        return

    # id
    elif current.startswith("/id"):
        get_id(msg)
        return

    # groups
    elif current.startswith("/groups"):
        bot.send_message(msg.chat.id, "<i>Группы, в которых состоит Козловский:</i>\n"
                                      "<b>Чтобы скопировать chat_id, нажмите на него.</b>\n\n" + groups_str, 'HTML')
        return

    # chat228
    elif current.startswith("/chat"):
        if len(args) == 1:
            bot.send_message(msg.chat.id,
                             "Использование: /chat chat_id \n"
                             "chat_id - id чата, с которым ты будешь общаться от имени Козловского. \n"
                             "/id - получить chat_id человека. \n"
                             "/groups - получить chat_id группы.")
            return
        start_chat(str(msg.chat.id), args[1])
    else:
        try:
            my_index = chat_id_my.index(str(msg.chat.id))  # мы
            reply = None
            try:
                reply = chat_msg_pen[my_index][chat_msg_my[my_index].index(msg.reply_to_message.message_id)]
            except AttributeError:
                pass
            chat_msg_my[my_index].append(msg.id)
            chat_msg_pen[my_index].append(
                bot.copy_message(chat_id_pen[my_index], msg.chat.id, msg.id, reply_to_message_id=reply).message_id)
            save()
        except ValueError:
            pass
        except telebot.apihelper.ApiTelegramException as err:
            bot.send_message(msg.chat.id, "<b>Этому человеку невозможно написать через Козловского."
                                          "Он ещё не общался со мной.</b><i>(" + str(err.description) + ")</i>", 'HTML')

    # fun
    if str(msg.chat.id) not in chat_id_my and str(msg.chat.id) not in wait_for_chat_id:
        # random
        if any(s in args for s in randoms):
            start_num = 1
            end_num = 6
            try:
                start_index = args.index("от")
                start_num = int(args[start_index + 1])
            except ValueError:
                pass
            try:
                end_index = args.index("до")
                end_num = int(args[end_index + 1])
            except ValueError:
                pass
            if start_num > end_num:
                start_num, end_num = end_num, start_num
            bot.send_message(msg.chat.id,
                             f"Случайное число от {start_num} до {end_num}: {random.randint(start_num, end_num)}")
            return
        # image search
        if any(s in current for s in searches):
            try:
                photo_search(msg.chat.id, msg.photo[-1])
            except (TypeError, AttributeError):
                try:
                    photo_search(msg.chat.id, msg.reply_to_message.photo[-1])
                    return
                except (TypeError, AttributeError):
                    pass
        # goroda game
        try:
            index = active_goroda.index(str(msg.chat.id))
            if any(s in args for s in ends):
                active_goroda.pop(index)
                current_letters.pop(index)
                bot.send_message(msg.chat.id, "<b>Конец игры</b>", "HTML")
                save()
                return
            city = n(current) + n(msg.caption)
            if city != "":
                if city[0] == current_letters[index] or current_letters[index] == "":
                    try:
                        random_city = random.choice(goroda[get_city_letter(city)])
                        bot.send_message(msg.chat.id, random_city)
                        current_letters[index] = get_city_letter(random_city)
                        save()
                    except IndexError:
                        bot.send_message(msg.chat.id, "<b>Невозможно сгенерировать город</b>")
                else:
                    bot.send_message(msg.chat.id, f"<b>Слово должно начинаться на букву:</b>  "
                                                  f"<i>{current_letters[index].upper()}</i>", "HTML")
                return
        except ValueError:
            if "в города" in current:
                active_goroda.append(str(msg.chat.id))
                current_letters.append("")
                bot.send_message(msg.chat.id, "<b>Вы начали игру в города.</b>\n<i>Начинайте первым!</i>", "HTML")
                save()
        # ai talk
        ai_talk(str(msg.chat.id), n(msg.text) + n(msg.caption), args, msg.chat.type == "private")


@bot.callback_query_handler(func=lambda call: 'btn' in call.data)
def query(call):
    data = str(call.data)
    if data.startswith("btn_ignore_"):
        ignore.append(data.split("btn_ignore_")[1])
        bot.edit_message_reply_markup(call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
        save()
    elif data.startswith("btn_chat_"):
        start_chat(str(call.message.chat.id), data.split("btn_chat_")[1])
    elif data.startswith("btn_photo_"):
        file_id = data.split("btn_photo_")[1]
        photo_id = images.get(file_id)
        bot.send_chat_action(call.message.chat.id, action="upload_photo")
        if photo_id is None:
            photo_id = bot.send_photo(call.message.chat.id,
                                      bot.download_file(bot.get_file(file_id).file_path)).photo[0].file_id
            images.setdefault(file_id, photo_id)
            save()
        else:
            bot.send_photo(call.message.chat.id, photo_id)

    elif data.startswith("btn_pinned_"):
        forward = data.split("_")
        try:
            bot.forward_message(call.message.chat.id, forward[2], int(forward[3]))
        except telebot.apihelper.ApiTelegramException:
            try:
                bot.send_message(call.message.chat.id, f"<b>Закреп от: {forward[4]}</b>", 'HTML')
                bot.copy_message(call.message.chat.id, forward[2], int(forward[3]))
            except telebot.apihelper.ApiTelegramException:
                bot.send_message(call.message.chat.id, "Сообщение не закреплено")


@bot.edited_message_handler(content_types=content_types)
def on_edit(msg: telebot.types.Message):
    try:
        my_index = chat_id_my.index(str(msg.chat.id))
        bot.edit_message_text(msg.text, chat_id_pen[my_index],
                              chat_msg_pen[my_index][chat_msg_my[my_index].index(msg.id)])
    except ValueError:
        pass
    try:
        other_index = chat_id_pen.index(str(msg.chat.id))
        bot.edit_message_text(msg.text, chat_id_my[other_index],
                              chat_msg_my[other_index][chat_msg_pen[other_index].index(msg.id)])
    except ValueError:
        pass


def timer():
    while True:
        for key in auto_start:
            if key in chat_id_my or key in wait_for_chat_id:
                continue
            now = datetime.now(ZoneInfo("Europe/Moscow"))
            if auto_start[key] <= now.timestamp() and MIN_ALLOWED_HOUR <= now.hour <= MAX_ALLOWED_HOUR:
                bot.send_message(key, "<i>/ignore - запретить Козловскому самому начинать переписку</i>", "HTML",
                                 disable_notification=True)
                ai_talk(key, "Привет", ["привет"], auto_answer=random.choice(starts))
        time.sleep(1)


# Запуск бота
webserver.keep_alive()
timer_thread = Thread(target=timer)
timer_thread.start()
print("start")
bot.infinity_polling(timeout=30, long_polling_timeout=60)
