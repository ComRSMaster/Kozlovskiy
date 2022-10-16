import re
from threading import Thread

import tools
import webserver
from tools import *


@bot.message_handler(content_types=content_types)
def chatting(msg: telebot.types.Message):
    current = str(n(msg.text) + n(msg.caption)).lower()
    args = re.split(r'[ ,.;&!?@\[\]]+', current)
    # chat management
    if msg.chat.type == "private":
        new_private_cr(str(msg.chat.id))
    else:
        if msg.content_type in ["group_chat_created", "supergroup_chat_created", "channel_chat_created"]:
            new_group_cr(str(msg.chat.id), msg.chat.title)
    if msg.content_type == "migrate_to_chat_id":
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
        return
    # stats
    elif str(msg.chat.id) not in ignore:
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

    if users[str(msg.chat.id)].get("getting_id", 0):
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
        users[str(msg.chat.id)].pop("getting_id")
        save()

    # cancel
    if current.startswith("/cancel"):
        if users[str(msg.chat.id)].pop("getting_id", 0) != 0:
            bot.send_message(msg.chat.id, "Всё отменяю")
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
                bot.send_message(msg.chat.id, "Я совершенно свободен")
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

    # decrypt voice/video messages
    elif current.startswith("/d"):
        file_id = get_voice_id(msg)
        if file_id is None:
            bot.send_message(msg.chat.id,
                             "Ответьте на голосовое/видео сообщение этой командой /d, чтобы его расшифровать.")
            return
        bot.send_chat_action(msg.chat.id, action="typing")
        Thread(target=stt, args=[file_id, msg.reply_to_message]).start()
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
                             "Нажмите кнопку для выбора возможных чатов", "HTML",
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
            bot.send_message(msg.chat.id, "<b>Этому человеку невозможно написать через Козловского."
                                          "Он ещё не общался со мной.</b><i>(" + str(err.description) + ")</i>", 'HTML')

    # fun
    if str(msg.chat.id) not in chat_id_my:
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
        ai_talk(str(msg.chat.id), n(msg.text) + n(msg.caption), get_voice_id(msg), args, msg.chat.type == "private")


@bot.callback_query_handler(func=lambda call: 'btn' in call.data)
def query(call):
    data = str(call.data)
    if data.startswith("btn_ignore_"):
        ignore.append(data.split("btn_ignore_")[1])
        bot.edit_message_reply_markup(call.message.chat.id, message_id=call.message.message_id)
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


@bot.inline_handler(None)
def query_photo(inline_query):
    results = []
    exist_images = requests.get(webserver.url + "check").json()["images"] if is_local else None
    index = 0
    for user in users:
        index += 1
        current = bot.get_chat(user)
        if current.photo is None:
            thumb_url = None
        else:
            photo_id = current.photo.small_file_id
            file_name = photo_id + ".jpg"
            image_url = "i/" + file_name
            if is_local:
                if file_name not in exist_images:
                    requests.post(webserver.url + "upload/" + photo_id, data=bot.download_file(
                        bot.get_file(photo_id).file_path))
            else:
                if not os.path.exists(image_url):
                    with open(image_url, 'wb') as new_photo:
                        new_photo.write(bot.download_file(bot.get_file(photo_id).file_path))
            thumb_url = webserver.url + image_url
        results.append(telebot.types.InlineQueryResultArticle(
            index, current.title if current.type != "private" else current.first_name + n(current.last_name, " "),
            telebot.types.InputTextMessageContent("/chat " + user),
            description=(n(current.description) if current.type != "private" else n(
                current.bio)) + "\nНажмите, чтобы написать в этот чат", thumb_url=thumb_url))
    bot.answer_inline_query(inline_query.id, results)


@bot.my_chat_member_handler(None)
def ban_handler(member: telebot.types.ChatMemberUpdated):
    if member.new_chat_member.status in ["restricted", "kicked"]:
        users.pop(str(member.chat.id))
        try:
            ignore.remove(str(member.chat.id))
        except ValueError:
            pass
        try:
            birthdays.pop(str(member.chat.id))
        except KeyError:
            pass
        try:
            ai_datas.pop(str(member.chat.id))
        except KeyError:
            pass
        save()
        bot.send_message(admin_chat, "<b>Удалён чат:  <pre>" + str(member.chat.id) + "</pre></b>", "HTML")
    else:
        if member.chat.type == "private":
            new_private_cr(str(member.chat.id))
        else:
            new_group_cr(str(member.chat.id), member.chat.title)


# Запуск бота
webserver.keep_alive(is_local)
Thread(target=timer).start()
Thread(target=load_ai).start()
print("start")
bot.infinity_polling()
