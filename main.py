import configparser
import json
import os
import random
import re
import sys
import time
from datetime import datetime
from threading import Thread

if sys.version_info < (3, 9):
    # noinspection PyUnresolvedReferences,PyPackageRequirements
    from backports.zoneinfo import ZoneInfo
else:
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


content_types = [
    "text", "audio", "document", "photo", "sticker", "video", "video_note",
    "voice", "location", "contact", "group_chat_created",
    "supergroup_chat_created", "channel_chat_created", "migrate_to_chat_id",
    "poll"
]
admin_chat = "-1001624831175"
config = configparser.ConfigParser()
config.read("config.ini", encoding="utf8")  # читаем конфиг
TOKEN = os.getenv("Kozlovskiy_token")
bot = telebot.TeleBot(TOKEN, exception_handler=ExceptionHandler())


def save():
    config.set('Settings', 'ignore', json.dumps(ignore))
    config.set('Dump', 'images', json.dumps(images))
    config.set('Dump', 'current_chat', current_chat)
    config.set('Dump', 'current_user', current_user)
    config.set('Dump', 'auto_start', json.dumps(auto_start))
    config.set('Dump', 'users', json.dumps(users))
    config.set('Dump', 'groups', json.dumps(groups))
    config.set('Dump', 'birthdays', json.dumps(birthdays))
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


is_local = config.getboolean("Settings", 'is_local')
MIN_IGNORE_TIME = config.getint("Settings", "MIN_IGNORE_TIME")
MAX_IGNORE_TIME = config.getint("Settings", "MAX_IGNORE_TIME")
MIN_BIRTHDAY_HOUR = config.getint("Settings", "MIN_BIRTHDAY_HOUR")
MIN_ALLOWED_HOUR = config.getint("Settings", "MIN_ALLOWED_HOUR")
MAX_ALLOWED_HOUR = config.getint("Settings", "MAX_ALLOWED_HOUR")
ignore = json.loads(config["Settings"]['ignore'])
ans = json.loads(config["Settings"]['ans'])
starts = json.loads(config["Settings"]['starts'])
calls = json.loads(config["Settings"]['calls'])
calls_private = json.loads(config["Settings"]['calls_private'])
ends = json.loads(config["Settings"]['ends'])
searches = json.loads(config["Settings"]['searches'])
randoms = json.loads(config["Settings"]['randoms'])
images: dict = json.loads(config["Dump"]['images'])
current_chat = config["Dump"]['current_chat']
current_user = config["Dump"]['current_user']
auto_start: dict = json.loads(config["Dump"]['auto_start'])
users = json.loads(config["Dump"]['users'])
groups = json.loads(config["Dump"]['groups'])
birthdays: dict = json.loads(config["Dump"]['birthdays'])
active_goroda: list = json.loads(config["Dump"]['active_goroda'])
current_letters = json.loads(config["Dump"]['current_letters'])
wait_for_chat_id = json.loads(config["Dump"]['wait_for_chat_id'])
chat_id_my = json.loads(config["Dump"]['chat_id_my'])
chat_id_pen: list = json.loads(config["Dump"]['chat_id_pen'])
chat_msg_my = json.loads(config["Dump"]['chat_msg_my'])
chat_msg_pen = json.loads(config["Dump"]['chat_msg_pen'])
current_users = json.loads(config["Dump"]['current_users'])
ai_datas: dict = json.loads(config["Dump"]['ai_datas'])
uspeh = "BAACAgIAAxkBAAIjjWMc7GQV0ByLx8XNtpeqLGl0fMwvAAILHQACaqCJSCY92YbVoX6vKQQ"

with open('cities.json', encoding="utf-8") as f:
    goroda = json.loads(f.read())


def get_id(message):
    wait_for_chat_id.append(str(message.chat.id))
    bot.send_message(
        message.chat.id, "Теперь перешли мне любое сообщение из чата, "
                         "или поделись со мной контактом этого человека.\n /cancel - отмена")
    save()


def start_chat(chat_id, chat):
    try:
        if chat == chat_id:
            bot.send_message(chat_id, "<b>Нельзя писать самому себе через Козловского.</b>",
                             'HTML')
            return
        if chat_id in chat_id_my:
            bot.send_message(chat_id, "<b>Вы уже пишете кому-то через Козловского.\n"
                                      "Чтобы законичить, введите /cancel</b>", 'HTML')
            return
        chat_info = bot.get_chat(chat)
        markup = telebot.types.InlineKeyboardMarkup()
        if chat_info.photo is not None:
            markup.add(
                telebot.types.InlineKeyboardButton(
                    text="Посмотреть фото профиля",
                    callback_data="btn_photo_" + chat))
        if chat_info.pinned_message is not None:
            markup.add(
                telebot.types.InlineKeyboardButton(text="Посмотреть закреп",
                                                   callback_data=f"btn_pinned_{chat_info.pinned_message.chat.id}_"
                                                                 f"{chat_info.pinned_message.message_id}_"
                                                                 f"{chat_info.pinned_message.from_user.first_name}"))
        bot.send_message(chat_id, parse_chat(chat_info) +
                         "\n\n<b>/cancel - закончить переписку\n"
                         "/delete - удалить сообщение у собеседника</b>",
                         'HTML', reply_markup=markup)
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
    auto_start[chat_id] = int(datetime.now(ZoneInfo("Europe/Moscow")).timestamp()) + random.randint(
        MIN_IGNORE_TIME, MAX_IGNORE_TIME)


def ai_talk(chat_id: str, msg_text, args, is_private=True, auto_answer=""):
    try:
        msgs = ai_datas[chat_id]
        if any(s in args for s in ends):
            ai_datas.pop(chat_id)
            bot.send_message(chat_id, "Пока")
            save()
            return
        if msg_text != "":
            bot.send_chat_action(chat_id, action="typing")
            ai_datas[chat_id].append(msg_text)
            if auto_answer == "":
                res = requests.post('https://api.aicloud.sbercloud.ru/public/v2/boltalka/predict',
                                    json={"instances": [{"contexts": [msgs]}]}).json()
                answer = str(res["responses"][2:-2]).replace("%bot_name", random.choice(["Даня", "Козловский"]))
            else:
                answer = auto_answer
            if is_private and chat_id in auto_start:
                set_next_time(chat_id)
            bot.send_message(chat_id, answer, disable_notification=auto_answer != "")
            ai_datas[chat_id].append(answer)
            ai_datas[chat_id] = msgs[-20:]
            save()
    except KeyError:
        if any(s in args for s in calls) or (is_private and any(s in args for s in calls_private)):
            ai_datas.setdefault(chat_id, [])
            ai_talk(chat_id, msg_text, args, is_private, auto_answer)
            save()


def photo_search(chat_id, search_photo):
    bot.send_chat_action(chat_id, action="typing")
    url_pic = "https://yandex.ru/images/search?rpt=imageview&url=" + bot.get_file_url(
        search_photo.file_id)
    soup = BeautifulSoup(requests.get(url_pic).text, 'lxml')
    results_vk = soup.find('div', class_='CbirSites-ItemInfo')
    if 'vk.com/id' in results_vk.find('a').get('href'):
        bot.send_message(chat_id, results_vk.find('div', class_='CbirSites-ItemDescription').get_text())
        return
    results = soup.find('section', 'CbirTags').find_all('a')
    bot.send_message(
        chat_id, results[0].find('span').get_text() + ", " + results[1].find('span').get_text())


def todict(obj):
    data = {}
    for key, value in obj.__dict__.items():
        try:
            data[key] = todict(value)
        except AttributeError:
            data[key] = value
    return data


def n(text: str, addition=''):
    """Если text - None, то вернуть пустую строку"""
    try:
        return "" if text is None else addition + text
    except telebot.apihelper.ApiTelegramException:
        return ""


def parse_chat(chat: telebot.types.Chat):
    text = "<b>Начат чат с:</b>\n\n"
    if chat.type == "private":
        text += '<b>Человек<a href="tg://user?id=' + str(chat.id) + '">: ' + chat.first_name + \
                n(chat.last_name, ' ') + '</a></b>' + n(chat.bio, '\n<b>Описание:</b> ') + n(chat.username, '\n@')
    elif chat.type == "channel":
        return str(todict(chat))
    else:
        text += "<b>Группа:</b> " + chat.title + n(chat.description, '\n<b>Описание:</b> ') + \
                n(chat.username, '\n@') + n(chat.invite_link, '\n<b>Ссылка:</b> ')
        try:
            text += n(str(bot.get_chat_member_count(chat.id)), '\n<b>Участников:</b> ')
            text += "\n<b>Админы:</b> "
            for m in bot.get_chat_administrators(chat.id):
                text += '\n\n<b><a href="tg://user?id=' + str(m.user.id) + '">' + m.user.first_name + \
                        '</a></b> <pre>' + str(m.user.id) + '</pre> ' + n(m.user.username, '\n@')

        except telebot.apihelper.ApiTelegramException:
            pass
    return text


def get_available(exist_images, results, is_groups, start_index=0):
    index = 0
    for g in groups if is_groups else users:
        index += 1
        current = bot.get_chat(g)
        if current.photo is None:
            thumb_url = None
        else:
            photo_id = current.photo.small_file_id
            file_name = photo_id + ".jpg"
            image_url = "static/" + file_name
            if is_local:
                if file_name not in exist_images:
                    requests.post(webserver.url + "upload/" + file_name, data=bot.download_file(
                        bot.get_file(photo_id).file_path))
            else:
                if not os.path.exists(image_url):
                    with open(image_url, 'wb') as new_photo:
                        new_photo.write(bot.download_file(bot.get_file(photo_id).file_path))
            thumb_url = webserver.url + image_url
        results.append(
            telebot.types.InlineQueryResultArticle(
                index + start_index,
                current.title if is_groups else current.first_name + n(current.last_name, " "),
                telebot.types.InputTextMessageContent("/chat " + g),
                description=(n(current.description) if is_groups else n(
                    current.bio)) + "\nНажмите, чтобы написать в этот чат",
                thumb_url=thumb_url))
    return index


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
            bot.send_video(msg.chat.id, uspeh, caption="<b>Чем я могу помочь?</b>🤔", parse_mode="HTML")
            set_next_time(str(msg.chat.id))
            save()
    else:
        new_group = False
        if msg.content_type in ["group_chat_created", "supergroup_chat_created", "channel_chat_created"]:
            new_group = True
        else:
            for g in groups:
                if g == str(msg.chat.id):
                    break
            else:
                new_group = True
        if new_group:
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(
                telebot.types.InlineKeyboardButton(text="Ignore", callback_data="btn_ignore_" + str(msg.chat.id)))
            bot.send_message(admin_chat, "<b>Новая группа: " + msg.chat.title + "  <pre>" +
                             str(msg.chat.id) + "</pre></b>", 'HTML', reply_markup=markup)
            groups.append(str(msg.chat.id))
            save()
            return
    if msg.content_type == "migrate_to_chat_id":
        for g in range(len(groups)):
            if groups[g] == str(msg.chat.id):
                groups[g] = str(msg.migrate_to_chat_id)
                break
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
                bot.send_message(admin_chat, "<b>" + str(msg.chat.first_name) + " " +
                                 str(msg.chat.id) + "</b>", 'HTML')
            else:
                bot.send_message(admin_chat, "<b>" + str(msg.from_user.first_name) + " " +
                                 str(msg.from_user.id) + "\n " + str(msg.chat.title) + " " +
                                 str(msg.chat.id) + "</b>", 'HTML')
        bot.copy_message(admin_chat, msg.chat.id, msg.id)

    # voter
    if msg.content_type == "poll":
        bot.send_message(msg.chat.id, random.choice(msg.poll.options).text, reply_to_message_id=msg.id)

    # chat228
    try:
        for other_index in range(len(chat_id_pen)):
            if chat_id_pen[other_index] != str(msg.chat.id):  # собеседники
                continue
            if msg.chat.type != "private":
                if str(msg.from_user.id) not in current_users[other_index]:
                    current_users[other_index] = str(msg.from_user.id)
                    bot.send_message(chat_id_my[other_index], "<b>" + str(msg.from_user.first_name) + " <pre>" +
                                     str(msg.from_user.id) + "</pre></b>", 'HTML')
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

    if str(msg.chat.id) in wait_for_chat_id:
        markup = telebot.types.InlineKeyboardMarkup()
        if msg.content_type == 'contact':
            user_id = str(msg.contact.user_id)
            if user_id == "None":
                bot.send_message(msg.chat.id, "Этого человека нет в Telegram.")
                return
            else:
                markup.add(telebot.types.InlineKeyboardButton(text="Начать чат", callback_data="btn_chat_" + user_id))
                bot.send_message(msg.chat.id, user_id, reply_markup=markup)
                return
        else:
            try:
                chat_id = str(msg.forward_from.id)
                markup.add(telebot.types.InlineKeyboardButton(text="Начать чат", callback_data="btn_chat_" + chat_id))
                bot.send_message(msg.chat.id, chat_id, reply_markup=markup)
                return
            except AttributeError:
                pass
        wait_for_chat_id.remove(str(msg.chat.id))
        save()

    # cancel
    if current.startswith("/cancel"):
        try:
            wait_for_chat_id.remove(str(msg.chat.id))
            bot.send_message(msg.chat.id, "Всё отменяю")
            save()
            return
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
                return
            except ValueError:
                bot.send_message(msg.chat.id, "Я совершенно свободен")
                return

    # ignore
    if current.startswith("/ignore"):
        if msg.chat.type != "private":
            bot.send_message(msg.chat.id, "<i>Эту команду можно использовать только в лс</i>", 'HTML')
            return
        try:
            auto_start.pop(str(msg.chat.id))
            bot.send_message(msg.chat.id,
                             "<b>Теперь Козловский не будет начинать переписку сам.</b>\n"
                             "<i>Чтобы вернуть всё как было, введите /ignore ещё раз.</i>",
                             'HTML')
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

    # chat228
    elif current.startswith("/chat"):
        if len(args) == 1:
            bot.send_message(
                msg.chat.id, "Использование: /chat <b>chat_id</b> \n"
                             "<i>chat_id</i> - id чата, с которым ты будешь общаться от имени Козловского. \n"
                             "/id - получить <i>chat_id</i> <b>любого</b> человека.\n"
                             "Нажмите кнопку для выбора возможных чатов",
                "HTML",
                reply_markup=telebot.types.InlineKeyboardMarkup().add(
                    telebot.types.InlineKeyboardButton(text="Выбрать чат", switch_inline_query_current_chat="")))
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
            chat_msg_pen[my_index].append(bot.copy_message(chat_id_pen[my_index], msg.chat.id, msg.id,
                                                           reply_to_message_id=reply).message_id)
            save()
        except ValueError:
            pass
        except telebot.apihelper.ApiTelegramException as err:
            bot.send_message(msg.chat.id,
                             "<b>Этому человеку невозможно написать через Козловского."
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
                return
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
                    except KeyError:
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
                return
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
        bot.send_chat_action(call.message.chat.id, action="upload_photo")
        chat_id = data.split("btn_photo_")[1]
        chat_info = bot.get_chat(chat_id)
        if chat_info.type == "private":
            profile_photos: list = bot.get_user_profile_photos(int(chat_id)).photos
            chunks = [profile_photos[i:i + 10] for i in range(0, len(profile_photos), 10)]
            for c in chunks:
                media_group = []
                new_photos = []
                for i in range(len(c)):
                    photo_id = images.get(c[i][-1].file_id)
                    if photo_id is None:
                        photo_id = bot.download_file(bot.get_file(c[i][-1].file_id).file_path)
                        new_photos.append(i)
                    media_group.append(telebot.types.InputMediaPhoto(photo_id))
                sent_photos = bot.send_media_group(call.message.chat.id, media_group)
                for i in new_photos:
                    images.setdefault(c[i][-1].file_id, sent_photos[i].photo[-1].file_id)
        else:
            file_id = chat_info.photo.big_file_id
            photo_id = images.get(file_id)
            if photo_id is None:
                photo_id = bot.send_photo(call.message.chat.id,
                                          bot.download_file(bot.get_file(file_id).file_path)).photo[-1].file_id
                images.setdefault(file_id, photo_id)
            else:
                bot.send_photo(call.message.chat.id, photo_id)
        save()

    elif data.startswith("btn_pinned_"):
        forward = data.split("_")
        try:
            bot.forward_message(call.message.chat.id, forward[2], int(forward[3]))
        except telebot.apihelper.ApiTelegramException:
            try:
                bot.send_message(call.message.chat.id, f"<b>Закреп от: {forward[4]}</b>", 'HTML')
                bot.copy_message(call.message.chat.id, forward[2], int(forward[3]))
            except telebot.apihelper.ApiTelegramException:
                bot.send_message(call.message.chat.id,
                                 "Сообщение не закреплено")


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


@bot.inline_handler(None)
def query_photo(inline_query):
    results = []
    exist_images = requests.get(webserver.url + "check").json()["images"] if is_local else None
    get_available(exist_images, results, False, get_available(exist_images, results, True))
    bot.answer_inline_query(inline_query.id, results)


def timer():
    while True:
        now = datetime.now(ZoneInfo("Europe/Moscow"))
        for key in birthdays:
            if MIN_BIRTHDAY_HOUR <= now.hour and now.day == birthdays[key][0] and now.month == birthdays[key][1]:
                if not birthdays[key][2]:
                    bot.send_message(admin_chat, "Я поздравил с ДР: " + key)
                    bot.send_video(key, uspeh, caption="<b>Поздравляю тебя с днём рождения!</b>🎉🎉🎉",
                                   parse_mode="HTML")
                    birthdays[key][2] = 1
            else:
                birthdays[key][2] = 0
            save()

        for key in auto_start:
            if key in chat_id_my or key in wait_for_chat_id:
                continue
            if auto_start[key] <= now.timestamp() and MIN_ALLOWED_HOUR <= now.hour <= MAX_ALLOWED_HOUR:
                bot.send_message(admin_chat, "Я написал: " + key)
                bot.send_message(key, "<i>/ignore - запретить Козловскому самому начинать переписку</i>", "HTML",
                                 disable_notification=True)
                ai_talk(key, "Привет", ["привет"], auto_answer=random.choice(starts))
        time.sleep(1000)


# Запуск бота
webserver.keep_alive()
timer_thread = Thread(target=timer)
timer_thread.start()
print("start")
bot.infinity_polling()
