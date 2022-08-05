import random
import configparser
import telebot
import json

content_types = ["text", "audio", "document", "photo", "sticker", "video", "video_note", "voice", "location", "contact",
                 "new_chat_title", "group_chat_created", "supergroup_chat_created", "channel_chat_created",
                 "migrate_to_chat_id", "poll"]
admin = "-1001624831175"
config = configparser.ConfigParser()
config.read("config.ini", encoding="utf8")  # читаем конфиг
bot = telebot.TeleBot(config["Settings"]['token'])


def update_groups(load=False):
    global groups
    global groups_str
    with open("groups.txt", "r+", encoding="utf-8") as groups_file:
        if load:
            groups = [chat.split(':  ') for chat in groups_file.readlines()]
        else:
            groups_file.truncate()
            groups_file.writelines(str(x) + ':  ' + str(y) for x, y in groups)
    groups_str = ''.join('`' + str(x) + '`:  *' + str(y) + '*' for x, y in groups)


def save():
    config.set('Settings', 'ignore', json.dumps(ignore))
    config.set('Settings', 'images', json.dumps(images))
    config.set('Dump', 'current_chat', current_chat)
    config.set('Dump', 'current_user', current_user)
    config.set('Dump', 'active_chats', json.dumps(active_chats))
    config.set('Dump', 'wait_for_chat_id', json.dumps(wait_for_chat_id))
    config.set('Dump', 'chat_id_my', json.dumps(chat_id_my))
    config.set('Dump', 'chat_id_pen', json.dumps(chat_id_pen))
    config.set('Dump', 'chat_msg_my', json.dumps(chat_msg_my))
    config.set('Dump', 'chat_msg_pen', json.dumps(chat_msg_pen))
    config.set('Dump', 'current_users', json.dumps(current_users))
    with open('config.ini', 'w', encoding="utf-8") as f:
        config.write(f)


groups = []
groups_str = ""
update_groups(True)

ignore = json.loads(config["Settings"]['ignore'])
ans = json.loads(config["Settings"]['ans'])
ans_voice = json.loads(config["Settings"]['ans_voice'])
images: dict = json.loads(config["Settings"]['images'])
starts = json.loads(config["Settings"]['starts'])
calls = json.loads(config["Settings"]['calls'])
ends = json.loads(config["Settings"]['ends'])
randoms = json.loads(config["Settings"]['randoms'])

current_chat = config["Dump"]['current_chat']
current_user = config["Dump"]['current_user']
active_chats = json.loads(config["Dump"]['active_chats'])
wait_for_chat_id = json.loads(config["Dump"]['wait_for_chat_id'])
chat_id_my = json.loads(config["Dump"]['chat_id_my'])
chat_id_pen = json.loads(config["Dump"]['chat_id_pen'])
chat_msg_my = json.loads(config["Dump"]['chat_msg_my'])
chat_msg_pen = json.loads(config["Dump"]['chat_msg_pen'])
current_users = json.loads(config["Dump"]['current_users'])


def get_id(message):
    wait_for_chat_id.append(str(message.chat.id))
    bot.send_message(message.chat.id,
                     "Теперь перешли мне любое сообщение из чата, "
                     "или поделись со мной контактом этого человека.\n /cancel - отмена")
    save()


def start_chat(chat_id, chat):
    try:
        if chat == chat_id:
            bot.send_message(chat_id, "*Нельзя писать самому себе через Козловского.*", 'Markdown')
            return
        if chat_id in chat_id_my:
            bot.send_message(chat_id,
                             "*Вы уже пишете кому-то через Козловского.\nЧтобы законичить, введите /cancel*",
                             'Markdown')
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


def todict(obj):
    data = {}
    for key, value in obj.__dict__.items():
        try:
            data[key] = todict(value)
        except AttributeError:
            data[key] = value
    return data


def n(text, addition=''):
    """если text - None, то вернуть пустую строку"""
    return "" if text is None else addition + text


def parse_chat(chat: telebot.types.Chat):
    text = "<b>Начат чат с:</b>\n\n"
    if chat.type == "private":
        text += "Человек: " + chat.first_name + n(chat.last_name, ' ') + \
                n(chat.bio, '\nОписание: ') + n(chat.username, '\n@')
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

    current = str(msg.text).lower()
    args = current.split(" ")[1:]
    # group management
    if msg.chat.type != "private":
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
            bot.send_message(admin, "*Новая группа: " + msg.chat.title + "  " + str(msg.chat.id) + "*", 'Markdown',
                             reply_markup=markup)
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
                bot.send_message(admin, "*" +
                                 str(msg.chat.first_name) + " " + str(msg.chat.id) + "*", 'Markdown')
            else:
                bot.send_message(admin, "*" +
                                 str(msg.from_user.first_name) + " " + str(msg.from_user.id) + "\n " +
                                 str(msg.chat.title) + " " + str(msg.chat.id) + "*", 'Markdown')
        bot.copy_message(admin, msg.chat.id, msg.id)

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
                bot.send_message(chat_id_my[other_index],
                                 "*" + str(msg.from_user.first_name) + " " + str(msg.from_user.id) + "*", 'Markdown')
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

    # delete
    if current.startswith("/delete"):
        try:
            reply = msg.reply_to_message.message_id
            my_index = chat_id_my.index(str(msg.chat.id))
            bot.delete_message(chat_id_pen[my_index], chat_msg_pen[my_index][chat_msg_my[my_index].index(reply)])
            bot.send_message(msg.chat.id, "_Сообщение удалено._", 'Markdown')
        except AttributeError:
            bot.send_message(msg.chat.id, "Ответьте командой /delete на сообщение, которое требуется удалить.")
        except telebot.apihelper.ApiTelegramException:
            bot.send_message(msg.chat.id, "_Не удалось удалить сообщение._", 'Markdown')
        except ValueError:
            pass

    # id
    elif current.startswith("/id"):
        get_id(msg)

    # groups
    elif current.startswith("/groups"):
        bot.send_message(msg.chat.id, "_Группы, в которых состоит Козловский:_\n"
                                      "*Чтобы скопировать chat-id, нажмите на него.*\n\n" + groups_str, 'Markdown')

    # chat228
    elif current.startswith("/chat"):
        if len(args) == 0:
            bot.send_message(msg.chat.id,
                             "Использование: /chat chat_id \n"
                             "chat_id - id чата, с которым ты будешь общаться от имени Козловского. \n"
                             "/id - получить chat_id человека. \n"
                             "/groups - получить chat_id группы.")
            return
        start_chat(str(msg.chat.id), args[0])
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
            if err.error_code == 403:
                bot.send_message(msg.chat.id,
                                 "*Этому человеку невозможно написать через Козловского. Он ещё не общался со мной.*_("
                                 + str(err.description) + ")_",
                                 'Markdown')
            else:
                bot.send_message(msg.chat.id, "Ошибка: " + str(err))

    # fun
    if str(msg.chat.id) not in chat_id_my and str(msg.chat.id) not in wait_for_chat_id:
        # random
        if any(s in current for s in randoms) or current.startswith("/random"):
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
        # magic ball
        elif str(msg.chat.id) in active_chats:
            if any(s in current for s in ends):
                active_chats.remove(str(msg.chat.id))
                bot.send_message(msg.chat.id, "Пока")
                save()
            else:
                if msg.content_type == "voice":
                    bot.send_voice(msg.chat.id, random.choice(ans_voice))
                else:
                    bot.send_message(msg.chat.id, random.choice(ans))
        elif any(s in current for s in calls) or current.startswith(
                "/start"):
            active_chats.append(str(msg.chat.id))
            bot.send_message(msg.chat.id, random.choice(starts))
            save()


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
        sticker_id = images.get(file_id)
        if sticker_id is None:
            sticker_id = bot.send_sticker(call.message.chat.id,
                                          bot.download_file(bot.get_file(file_id).file_path)).sticker.file_id
            images.setdefault(file_id, sticker_id)
            save()
        else:
            bot.send_sticker(call.message.chat.id, sticker_id)

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


# Запуск бота
print("start")
bot.infinity_polling(timeout=30, long_polling_timeout=60)
