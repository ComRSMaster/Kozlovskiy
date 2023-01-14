#!/usr/bin/python3
from threading import Thread

import telebot.types

import tools
from tools import *


@bot.message_handler(commands=['start'])
def command_start(msg: telebot.types.Message):
    if chat_management(msg):
        ai_talk(msg.text, str(msg.chat.id), start="О чём поговорим?🤔", send=True)


@bot.message_handler(commands=['help'])
def command_help(msg: telebot.types.Message):
    bot.send_message(msg.chat.id, help_text, 'HTML')
    chat_management(msg)


@bot.message_handler(commands=['books'])
def command_books(msg: telebot.types.Message):
    bot.send_message(msg.chat.id, book_orig_text, 'HTML',
                     reply_markup=telebot.util.quick_markup(
                         {grade: {'callback_data': f'btn_grade_{grade}'} for grade in abstracts}, 5))
    chat_management(msg)


@bot.message_handler(commands=['done'])
def command_done(msg: telebot.types.Message):
    if users[str(msg.chat.id)]['s'] == "wait_for_done":
        users[str(msg.chat.id)]['s'] = "wait_for_pub"
        users[str(msg.chat.id)]['sd']['z'] = str(msg.chat.id)
        markup = telebot.types.ReplyKeyboardMarkup(
            input_field_placeholder="Чей конспект?", row_width=1, resize_keyboard=True).add(
            telebot.types.KeyboardButton(
                f'{msg.from_user.id}; {msg.from_user.first_name + n(msg.from_user.last_name, " ")}  (вы)'),
            *[telebot.types.KeyboardButton(f'{a}; {name}') for a, name in users[str(msg.chat.id)]['sd']['a'].items()])
        bot.send_message(
            msg.chat.id,
            "От имени кого ты хочешь выложить конспект?\nВыбери внизу, или поделись со мной "
            "контактом этого человека, или перешли от него любое сообщение, или напиши его имя",
            reply_markup=markup)
        save()
    elif users[str(msg.chat.id)]['s'] == "wait_for_pub":
        book_data = users[str(msg.chat.id)]['sd']
        grade, subject, book = book_data['data']
        unix = book_data['d'] if 'd' in book_data else msg.date
        book = f'{book} ({datetime.fromtimestamp(unix, ZoneInfo("Europe/Moscow")).year})'
        abstracts[grade][subject].append({'n': book, 'id': book_data['id'], 'a': book_data['z'], 't': unix})
        bot.send_message(msg.chat.id,
                         f'<b>Ваш конспект "{book}" успешно выложен!\n🎓 {grade} класс, {subject}</b>', 'HTML',
                         reply_markup=telebot.types.ReplyKeyboardRemove())
        users[str(msg.chat.id)]['s'] = ''
        users[str(msg.chat.id)].pop('sd')
        save()

    chat_management(msg)


@bot.message_handler(commands=['chat'])
def command_chat(msg: telebot.types.Message):
    chat_id = telebot.util.extract_arguments(msg.text)
    if chat_id:
        bot.send_message(
            msg.chat.id, "Эта команда позволяет писать <b>анонимно</b> другим людям.\n\n"
                         "<i>Использование:</i> /chat <i>chat_id</i>\n"
                         "/id - получить <i>chat_id</i> <b>любого</b> человека.\n"
                         "<b>⬇ Нажмите кнопку ниже для выбора чата ⬇</b>", "HTML",
            reply_markup=telebot.util.quick_markup({'Выбрать чат 💬': {'switch_inline_query_current_chat': ''}}))
    else:
        start_chat(str(msg.chat.id), chat_id)
    chat_management(msg)


@bot.message_handler(commands=['id'])
def command_id(msg: telebot.types.Message):
    users[str(msg.chat.id)]['s'] = "getting_id"
    bot.send_message(msg.chat.id, "Теперь перешли мне любое сообщение из чата, "
                                  "или поделись со мной контактом этого человека.\n /cancel - отмена")
    save()
    chat_management(msg)


@bot.message_handler(commands=['d'])
def command_d(msg: telebot.types.Message):
    file_id = get_voice_id(msg, True)
    if file_id is None:
        bot.send_message(msg.chat.id,
                         "<b>Ответьте на голосовое/видео сообщение командой /d, чтобы его расшифровать.</b>"
                         "\n<i>Если вы сделали всё правильно и видите это сообщение, "
                         "то перешлите сюда это голосовое</i>", 'HTML')
    else:
        stt(file_id, msg.reply_to_message)
    chat_management(msg)


@bot.message_handler(commands=['rnd'])
def command_rnd(msg: telebot.types.Message):
    nums = re.findall(r'\d+', msg.text)
    start_num = 1 if len(nums) < 2 else int(nums[0])
    end_num = 6 if len(nums) == 0 else int(nums[0]) if len(nums) == 1 else int(nums[1])
    if start_num > end_num:
        start_num, end_num = end_num, start_num
    bot.send_message(msg.chat.id,
                     f"🎲 Случайное число от {start_num} до {end_num}:  {random.randint(start_num, end_num)}")
    chat_management(msg)


@bot.message_handler(commands=['up'])
def command_up(msg: telebot.types.Message):
    file_id = None
    if msg.reply_to_message is not None:
        if msg.reply_to_message.content_type == "photo":
            file_id = msg.reply_to_message.photo[-1].file_id
        elif msg.reply_to_message.content_type == "document":
            file_id = msg.reply_to_message.document.file_id
    try:
        scale = float(telebot.util.extract_arguments(msg.text))
    except ValueError:
        scale = 0
    if file_id is None:
        bot.send_message(msg.chat.id,
                         "<b>✨Улучшение качества фото через нейросеть✨</b>\n\n"
                         "Чтобы улучшить фото, отправь его прямо сейчас <i>(желательно без сжатия)\n"
                         "Также можно ответить командой <code>/up N</code> на уже отправленное фото, "
                         "где N - масштаб улучшения</i>", 'HTML',
                         reply_markup=telebot.types.ForceReply(input_field_placeholder="Отправь фото"))
        users[str(msg.chat.id)]['s'] = 'up_photo'
        save()
    elif scale:
        gfpgan(msg.chat.id, file_id, scale)
    else:
        bot.send_message(msg.chat.id,
                         "<b>✨Улучшение качества фото через нейросеть✨</b>\n\n"
                         "Чтобы улучшить фото, отправь сейчас масштаб улучшения,"
                         "например, 2 - увеличение качества в 2 раза\n"
                         "<i>Также можно ответить командой <code>/up N</code> на уже отправленное фото, "
                         "где N - масштаб улучшения</i>", 'HTML',
                         reply_markup=telebot.types.ForceReply(input_field_placeholder="Отправь масштаб"))
        users[str(msg.chat.id)]['s'] = 'up_scale'
        users[str(msg.chat.id)]['sd'] = file_id
        save()
    chat_management(msg)


@bot.message_handler(commands=['delete'])
def command_delete(msg: telebot.types.Message):
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
    chat_management(msg)


@bot.message_handler(commands=['kill_bot'])
def command_kill_bot(msg: telebot.types.Message):
    # kill bot (admin only)
    if msg.chat.id == admin_chat:
        bot.remove_webhook()
        bot.send_message(msg.chat.id, "Бот успешно отключен")
        print("bot killed")
        # noinspection PyProtectedMember
        os._exit(0)
    chat_management(msg)


@bot.message_handler(commands=['exec'])
def command_exec(msg: telebot.types.Message):
    # exec command (admin only)
    if msg.chat.id == admin_chat:
        code_out = StringIO()
        sys.stdout = code_out
        try:
            exec(msg.text[6:])
        except Exception as e:
            bot.send_message(msg.chat.id, "ОШИБКА: " + str(e))
            return
        finally:
            sys.stdout = sys.__stdout__
        o = code_out.getvalue()
        if o == '':
            o = "Ничего не выведено"
        bot.send_message(msg.chat.id, o)
    chat_management(msg)


@bot.message_handler(commands=['cancel'])
def command_cancel(msg: telebot.types.Message):
    if users[str(msg.chat.id)]['s']:
        users[str(msg.chat.id)]['s'] = ''
        users[str(msg.chat.id)].pop('sd', 0)
        bot.send_message(msg.chat.id, "<b>Всё отменяю!</b>", 'HTML', reply_markup=telebot.types.ReplyKeyboardRemove())
        save()
    else:
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
            bot.send_message(msg.chat.id, "Я совершенно свободен", reply_markup=telebot.types.ReplyKeyboardRemove())
    chat_management(msg)


def chat_management(msg: telebot.types.Message):
    if str(msg.chat.id) not in ignore:  # copy messages to admin
        if str(msg.chat.id) != tools.current_chat:
            tools.current_chat = str(msg.chat.id)
            save()
            if msg.chat.type == "private":
                bot.send_message(admin_chat, "<b>" + str(msg.chat.first_name) + " " +
                                 str(msg.chat.id) + "</b>", 'HTML')
            else:
                bot.send_message(admin_chat, "<b>" + str(msg.from_user.first_name) + " " +
                                 str(msg.from_user.id) + "\n " + str(msg.chat.title) + " " +
                                 str(msg.chat.id) + "</b>", 'HTML')
        bot.copy_message(admin_chat, msg.chat.id, msg.id)
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
    if msg.chat.type == "private" and users.get(str(msg.chat.id)) is None:
        new_private_cr(msg.chat)
        return False
    else:
        return True


@bot.message_handler(content_types=["migrate_to_chat_id"])
def migrate_to_chat_id(msg: telebot.types.Message):
    users[str(msg.migrate_to_chat_id)] = users.pop(str(msg.chat.id))
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


@bot.message_handler(content_types=["new_chat_title", "new_chat_photo", "delete_chat_photo"])
def chat_info_changed(msg: telebot.types.Message):
    if msg.new_chat_title is not None:
        users[str(msg.chat.id)]['name'] = msg.new_chat_title
    if msg.new_chat_photo is not None:
        users[str(msg.chat.id)]['photo_id'] = msg.new_chat_photo[0].file_unique_id
        with open(f'website/p/{msg.new_chat_photo[0].file_unique_id}.jpg', 'wb') as file:
            file.write(bot.download_file(bot.get_file(msg.new_chat_photo[0].file_id).file_path))
    if msg.delete_chat_photo:
        users[str(msg.chat.id)]['photo_id'] = None
    save()


@bot.message_handler(content_types=["group_chat_created", "supergroup_chat_created", "channel_chat_created"])
def new_chat_created(msg: telebot.types.Message):
    new_group_cr(msg.chat)


@bot.message_handler(content_types=content_types)
def chatting(msg: telebot.types.Message):
    current = str(n(msg.text) + n(msg.caption)).lower()
    args = re.split(r'[ ,.;&!?\[\]]+', current)
    chat_management(msg)
    # voter
    if msg.content_type == "poll":
        bot.send_message(msg.chat.id, random.choice(msg.poll.options).text, reply_to_message_id=msg.id)
    state = users[str(msg.chat.id)]['s']
    if state == "wait_for_book_name":
        name = n(msg.text) + n(msg.caption)
        if name:
            grade, subject = users[str(msg.chat.id)]['sd']
            users[str(msg.chat.id)]['s'] = "wait_for_book"
            users[str(msg.chat.id)]['sd'] = {'id': {'d': [], 'p': [], 'u': ''}, 'data': (grade, subject, name),
                                             'a': {}, 'g': ''}
            bot.send_message(msg.chat.id, f"Конспект успешно назван: <b>{name}</b>", 'HTML')
            bot.send_message(msg.chat.id, f"<b>Теперь отправь файлы, фото, или ссылку с готовым конспектом</b>", 'HTML',
                             reply_markup=telebot.types.ForceReply(input_field_placeholder="Отправь конспект"))
            save()
        else:
            bot.send_message(msg.chat.id, "Попробуй назвать свой конспект ещё раз нормально")
        return
    elif state == "wait_for_book" or state == "wait_for_done":
        if msg.content_type == "photo":
            users[str(msg.chat.id)]['sd']['id']['p'].append(msg.photo[-1].file_id)
        elif msg.content_type == "document":
            users[str(msg.chat.id)]['sd']['id']['d'].append(msg.document.file_id)
        elif msg.content_type == "text" and msg.entities is not None and any(e.type == 'url' for e in msg.entities):
            users[str(msg.chat.id)]['sd']['id']['u'] += msg.text + '\n\n'
        else:
            bot.send_message(msg.chat.id, "<b>В конспекты можно отправлять только файлы, "
                                          "ссылки, фото или фото без сжатия!</b>", 'HTML')
            save()
            return
        if msg.forward_from is not None:
            if msg.forward_from.id != msg.from_user.id:
                users[str(msg.chat.id)]['sd']['a'][
                    msg.forward_from.id] = msg.forward_from.first_name + n(msg.forward_from.last_name, " ")
            users[str(msg.chat.id)]['sd']['d'] = msg.forward_date
        if msg.media_group_id is None or msg.media_group_id != users[str(msg.chat.id)]['sd']['g']:
            users[str(msg.chat.id)]['s'] = "wait_for_done"
            bot.send_message(msg.chat.id, "<b>Чтобы выложить конспект, используй команду /done</b>", 'HTML')
        users[str(msg.chat.id)]['sd']['g'] = msg.media_group_id
        save()
        return
    elif state == "getting_id" or state == "wait_for_pub":
        is_pub = state == "wait_for_pub"
        if is_pub:
            markup = None
        else:
            users[str(msg.chat.id)]['s'] = ''
            save()
            markup = telebot.types.InlineKeyboardMarkup()
        if msg.content_type == 'contact':
            chat_id = msg.contact.user_id
            if not chat_id:
                bot.send_message(msg.chat.id, "Этого человека нет в Telegram.")
            else:
                if is_pub:
                    author_name = f'<a href="tg://user?id={chat_id}">' \
                                  f'{msg.contact.first_name + n(msg.contact.last_name, " ")}</a>'
                    bot.send_message(
                        msg.chat.id, f"Конспект будет выложен от: <b>{author_name}</b> ?\n/done - выложить", 'HTML')
                    users[str(msg.chat.id)]['sd']['z'] = str(chat_id)
                    save()
                else:
                    markup.add(telebot.types.InlineKeyboardButton(text="Начать чат",
                                                                  callback_data=f"btn_chat_{chat_id}"))
                    bot.send_message(msg.chat.id, chat_id, reply_markup=markup)
            return
        elif msg.forward_from is not None:
            chat_id = msg.forward_from.id
            if is_pub:
                author_name = f'<a href="tg://user?id={chat_id}">' \
                              f'{msg.forward_from.first_name + n(msg.forward_from.last_name, " ")}</a>' \
                              f' {n(msg.forward_from.username, "@")}'
                bot.send_message(msg.chat.id, f"Конспект будет выложен от: <b>{author_name}</b>\n"
                                              f"/done - выложить", 'HTML')
                users[str(msg.chat.id)]['sd']['z'] = str(chat_id)
                save()
            else:
                markup.add(telebot.types.InlineKeyboardButton(text="Начать чат",
                                                              callback_data=f"btn_chat_{chat_id}"))
                bot.send_message(msg.chat.id, chat_id, reply_markup=markup)
            return
        elif is_pub:
            if msg.content_type == 'text':
                name = msg.text
                chat_id = name
                ids = name.find('; ')
                if ids != -1:
                    chat_id = name[:ids]
                    name = name[ids + 2:]
                bot.send_message(msg.chat.id, f"Конспект будет выложен от: <b>{name}</b> ?\n"
                                              f"/done - выложить", 'HTML')
                users[str(msg.chat.id)]['sd']["z"] = chat_id
                save()
            else:
                bot.send_message(msg.chat.id, "Попробуй ещё раз")
            return
    elif state == "up_scale":
        try:
            scale = float(msg.text)
            gfpgan(msg.chat.id, users[str(msg.chat.id)]['sd'], scale)
            users[str(msg.chat.id)]['s'] = ''
            users[str(msg.chat.id)].pop('sd', 0)
            save()
        except ValueError:
            bot.send_message(msg.chat.id, "Масштаб должен быть числом, отправь масштаб ещё раз",
                             reply_markup=telebot.types.ForceReply(input_field_placeholder="Отправь масштаб"))
        return
    elif state == "up_photo":
        if msg.content_type == "photo":
            file_id = msg.photo[-1].file_id
        elif msg.content_type == "document":
            file_id = msg.document.file_id
        else:
            bot.send_message(msg.chat.id,
                             "Можно улучшить только обычные фото или фото без сжатия, отправь фото ещё раз",
                             reply_markup=telebot.types.ForceReply(input_field_placeholder="Отправь фото"))
            return
        bot.send_message(msg.chat.id,
                         "Теперь отправь масштаб улучшения, например, 2 - увеличение качества в 2 раза",
                         reply_markup=telebot.types.ForceReply(input_field_placeholder="Отправь масштаб"))
        users[str(msg.chat.id)]['s'] = 'up_scale'
        users[str(msg.chat.id)]['sd'] = file_id
        save()
        return
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
        return
    except telebot.apihelper.ApiTelegramException as err:
        bot.send_message(msg.chat.id, "<b>Этому человеку невозможно написать через Козловского.</b>"
                                      "<i>(" + str(err.description) + ")</i>", 'HTML')
        return
    except ValueError:
        pass
    # image search
    if any(s in current for s in searches):
        if msg.content_type == 'photo':
            photo_search(msg.chat.id, msg.id, msg.photo[-1])
            return
        elif msg.reply_to_message is not None and msg.reply_to_message.content_type == 'photo':
            photo_search(msg.chat.id, msg.reply_to_message.id, msg.reply_to_message.photo[-1])
            return
    # cities game
    if 'letter' in users[str(msg.chat.id)]:
        if 'complex_msg' in users[str(msg.chat.id)]:
            bot.edit_message_text(
                f"<b>Запущена игра в города.</b>\n<i>Начинай первым!</i>\n\n"
                f"Сложность: <b>{'ХАРДКОР' if users[str(msg.chat.id)]['complex'] == 'h' else 'ЛЕГКО'}</b>",
                msg.chat.id, users[str(msg.chat.id)]['complex_msg'], parse_mode="HTML")
            users[str(msg.chat.id)].pop('complex_msg')
        if any(s in args for s in ends):
            users[str(msg.chat.id)].pop('letter')
            users[str(msg.chat.id)].pop('complex')
            users[str(msg.chat.id)].pop('complex_msg', 0)
            bot.send_message(msg.chat.id, "<b>Конец игры</b>", "HTML")
            save()
            return
        if current:
            letter = users[str(msg.chat.id)]['letter']
            if current[0] == letter or letter == '':
                try:
                    cities_db = cities_hard if users[str(msg.chat.id)]['complex'] == 'h' else cities_easy
                    random_city = random.choice(cities_db[get_city_letter(current)])
                    bot.send_message(msg.chat.id, random_city)
                    users[str(msg.chat.id)]['letter'] = get_city_letter(random_city)
                    save()
                except KeyError:
                    bot.send_message(msg.chat.id, "<b>Невозможно сгенерировать город</b>", "HTML")
            else:
                bot.send_message(msg.chat.id, f"<b>Слово должно начинаться на букву:</b>  "
                                              f"<i>{letter.upper()}</i>", "HTML")
            return
    elif "в города" in current:
        users[str(msg.chat.id)]['letter'] = ''
        users[str(msg.chat.id)]['complex'] = 'e'
        users[str(msg.chat.id)]['complex_msg'] = bot.send_message(
            msg.chat.id, "<b>Запущена игра в города.</b>\n<i>Начинай первым!</i>\n\n"
                         "Сложность: <b>ЛЕГКО</b>\n⬇<i>Выбери сложность⬇</i>", "HTML",
            reply_markup=telebot.util.quick_markup({"ЛЕГКО👌": {'callback_data': 'btn_complex_e'},
                                                    "🔥ХАРДКОР🔥": {'callback_data': 'btn_complex_h'}})).message_id
        save()
        return
    # ai talk
    ai_talk(n(msg.text) + n(msg.caption), str(msg.chat.id), msg.chat.type == 'private', args, msg_voice=msg)


@bot.callback_query_handler(func=lambda call: 'btn' in call.data)
def query(call: telebot.types.CallbackQuery):
    data = str(call.data)
    if data.startswith("btn_complex"):
        comp = data[-1:]
        bot.answer_callback_query(call.id, f"Выбрана сложность: {'ХАРДКОР' if comp == 'h' else 'ЛЕГКО'}")
        if users[str(call.message.chat.id)]['complex'] != comp:
            bot.edit_message_text(
                f"<b>Запущена игра в города.</b>\n<i>Начинай первым!</i>\n\n"
                f"Сложность: <b>{'ХАРДКОР' if comp == 'h' else 'ЛЕГКО'}</b>\n⬇<i>Выбери сложность⬇</i>",
                call.message.chat.id, users[str(call.message.chat.id)]['complex_msg'], parse_mode="HTML",
                reply_markup=telebot.util.quick_markup({"ЛЕГКО👌": {'callback_data': 'btn_complex_e'},
                                                        "🔥ХАРДКОР🔥": {'callback_data': 'btn_complex_h'}}))
            users[str(call.message.chat.id)]['complex'] = comp
    elif data.startswith("btn_grade") or data.startswith("btn_subj_back"):
        grade = data[data.rfind("_") + 1:]
        subjects = {"◀ Назад": {'callback_data': 'btn_back'}}
        subjects.update({f'{subject} ({len(abstracts[grade][subject])})': {
            'callback_data': f'btn_subject_{grade}_{subject}'} for subject in abstracts[grade]})
        bot.edit_message_text(
            "<b>📕Конспекты и готовые билеты📙</b>\n\n"
            f"<b>🎓 Класс:</b> {grade}\nТеперь выберите нужный предмет, "
            "чтобы <i>найти</i> или <i>выложить</i> нужный конспект", call.message.chat.id, call.message.message_id,
            parse_mode='HTML', reply_markup=telebot.util.quick_markup(subjects))
    elif data.startswith("btn_subject") or data.startswith("btn_bok_back"):
        fs = data.rfind("_")
        subject = data[fs + 1:]
        grade = data[data[:fs].rfind("_") + 1:fs]
        markup = telebot.types.InlineKeyboardMarkup(row_width=1).add(
            telebot.types.InlineKeyboardButton("◀ Назад", callback_data=f'btn_subj_back_{grade}'),
            telebot.types.InlineKeyboardButton("Обновить 🔄️", callback_data=f'btn_subject_{grade}_{subject}'),
            telebot.types.InlineKeyboardButton(
                "Выложить 🔼", callback_data=f'btn_upload_{grade}_{subject}'), row_width=3).add(
            *[telebot.types.InlineKeyboardButton(
                abstracts[grade][subject][b]["n"],
                callback_data=f'btn_book_{grade}_{subject}_{b}') for b in range(len(abstracts[grade][subject]))])
        try:
            bot.edit_message_text(
                f"<b>📕Конспекты и готовые билеты📙</b>\n\n<b>🎓 Класс:</b> {grade}\n<b>📗 {subject}</b>\n\n"
                f"<b>Найдено конспектов:</b> {len(abstracts[grade][subject])}\n<i>Также ты можешь выложить свой "
                f"конспект</i>", call.message.chat.id, call.message.message_id, parse_mode='HTML', reply_markup=markup)
        except telebot.apihelper.ApiTelegramException:
            bot.answer_callback_query(call.id, "Ничего нового😥", show_alert=True, cache_time=5)
    elif data.startswith("btn_book"):
        _, _, grade, subject, book = data.split("_")
        info = abstracts[grade][subject][int(book)]
        author_name = info["a"]
        try:
            author = bot.get_chat(int(author_name))
            author_name = f'<a href="tg://user?id={info["a"]}">' \
                          f'{author.first_name + n(author.last_name, " ")}</a> {n(author.username, "@")}'
        except (telebot.apihelper.ApiTelegramException, ValueError):
            pass
        docs = [telebot.types.InputMediaDocument(d) for d in info['id']['d']]
        photos = [telebot.types.InputMediaPhoto(d) for d in info['id']['p']]
        caption = f'{info["id"]["u"]}<b>{info["n"]}\nАвтор: {author_name}\nОпубликовано: ' \
                  f'{datetime.fromtimestamp(info["t"], ZoneInfo("Europe/Moscow")).strftime("%d.%m.%Y %H:%M")}</b>'
        if len(docs) > 0:
            docs[-1].caption = caption
            docs[-1].parse_mode = 'HTML'
        elif len(photos) > 0:
            photos[-1].caption = caption
            photos[-1].parse_mode = 'HTML'
        else:
            bot.send_message(call.message.chat.id, caption, 'HTML')
        for i in range(0, len(photos), 10):
            bot.send_media_group(call.message.chat.id, photos[i:i + 10])
        for i in range(0, len(docs), 10):
            bot.send_media_group(call.message.chat.id, docs[i:i + 10])
        bot.answer_callback_query(call.id, "Конспект отправлен!")
    elif data.startswith("btn_back"):
        bot.edit_message_text(book_orig_text, call.message.chat.id, call.message.message_id, parse_mode='HTML',
                              reply_markup=telebot.util.quick_markup({grade: {
                                  'callback_data': f'btn_grade_{grade}'} for grade in abstracts}, 5))
    elif data.startswith("btn_upload"):
        fs = data.rfind("_")
        subject = data[fs + 1:]
        grade = data[data[:fs].rfind("_") + 1:fs]
        bot.send_message(
            call.message.chat.id,
            f'<b>🎓 Класс:</b> {grade}\n<b>📗 {subject}</b>\n\n'
            f'<b>Чтобы выложить свой конспект, напиши его <i>название</i></b> '
            f'<i>(год будет подписан автоматически в его конце)</i>\n<i>/cancel - отмена</i>', 'HTML',
            reply_markup=telebot.types.ForceReply(input_field_placeholder="Введи название конспекта"))
        bot.answer_callback_query(call.id, "Следуй инструкциям!")
        users[str(call.message.chat.id)]['s'] = "wait_for_book_name"
        users[str(call.message.chat.id)]['sd'] = (grade, subject)
        save()
    elif data.startswith("btn_chat"):
        start_chat(str(call.message.chat.id), data[data.rfind("_") + 1:])
        bot.answer_callback_query(call.id, "Чат начат!")
    elif data.startswith("btn_photo"):
        chat_id = data[data.rfind("_") + 1:]
        try:
            chat_info = bot.get_chat(chat_id)
        except telebot.apihelper.ApiTelegramException:
            bot.answer_callback_query(call.id, "Чат не найден!")
            return
        if chat_info.photo is None:
            bot.answer_callback_query(call.id, "Фото профиля не найдены!")
            return
        if chat_info.type == "private":
            profile_photos: list = bot.get_user_profile_photos(int(chat_id)).photos
            media_group = []
            k = 0
            for c in telebot.util.chunks(profile_photos, 10):
                bot.send_chat_action(call.message.chat.id, action="upload_photo")
                for p in c:
                    k += 1
                    media_group.append(telebot.types.InputMediaPhoto(
                        images[p[-1].file_id] if p[-1].file_id in images else
                        bot.download_file(bot.get_file(p[-1].file_id).file_path)))
                sent_photos = bot.send_media_group(call.message.chat.id, media_group)
                for i in range(len(sent_photos)):
                    images[profile_photos[k - len(c) + i][-1].file_id] = sent_photos[i].photo[-1].file_id
                media_group.clear()
        else:
            bot.send_chat_action(call.message.chat.id, action="upload_photo")
            file_id = chat_info.photo.big_file_id
            photo_id = images[file_id] if file_id in images else bot.download_file(bot.get_file(file_id).file_path)
            images[file_id] = bot.send_photo(call.message.chat.id, photo_id).photo[-1].file_id
        bot.answer_callback_query(call.id, "Фото отправлены!")
        save()
    elif data.startswith("btn_pinned"):
        forward = data.split("_")
        try:
            bot.forward_message(call.message.chat.id, forward[2], int(forward[3]))
        except telebot.apihelper.ApiTelegramException:
            try:
                bot.send_message(call.message.chat.id, f"<b>Закреп от: {forward[4]}</b>", 'HTML')
                bot.copy_message(call.message.chat.id, forward[2], int(forward[3]))
            except telebot.apihelper.ApiTelegramException:
                bot.answer_callback_query(call.id, "Сообщение не закреплено!")
                return
        bot.answer_callback_query(call.id, "Закреп отправлен!")
    elif data.startswith("btn_ignore"):
        ignore.append(data[data.rfind("_") + 1:])
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
        save()


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
    index = 0
    for u in users:
        index += 1
        results.append(telebot.types.InlineQueryResultArticle(
            index, users[u]['name'], telebot.types.InputTextMessageContent("/chat " + u),
            description=users[u]['desc'] + "\nНажмите, чтобы написать " + (
                "этому человеку" if users[u]['private'] else "в эту группу"),
            thumb_url=None if users[u]['photo_id'] is None else f'{web_url}p/{users[u]["photo_id"]}.jpg'))
    bot.answer_inline_query(inline_query.id, results)


@bot.my_chat_member_handler(None)
def ban_handler(member: telebot.types.ChatMemberUpdated):
    if member.new_chat_member.status in ["restricted", "kicked", "left"]:
        users.pop(str(member.chat.id))
        try:
            ignore.remove(str(member.chat.id))
        except ValueError:
            pass
        save()
        bot.send_message(admin_chat, "<b>Удалён чат:  <pre>" + str(member.chat.id) + "</pre></b>", "HTML")
    elif member.chat.type != "private":
        new_group_cr(member.chat)


def parse_updates(json_string):
    bot.process_new_updates([telebot.types.Update.de_json(json_string)])


# Запуск бота
Thread(target=timer).start()
print("start")
if is_dev:
    bot.infinity_polling(skip_pending=True)
else:
    import webserver

    bot.set_webhook(url=web_url + TOKEN)
    webserver.parse_updates = parse_updates
    webserver.run_webserver(TOKEN)

    bot.remove_webhook()

print("finish")
