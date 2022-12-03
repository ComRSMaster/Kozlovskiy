#!/usr/bin/python3
import re
from io import StringIO
from threading import Thread

import tools
from tools import *


@bot.message_handler(commands=['start'])
def command_start(msg: telebot.types.Message):
    if msg.chat.type == "private":
        if new_private_cr(msg.chat):
            chat_management(msg)
            return
    ai_talk(msg.text, str(msg.chat.id), start="О чём поговорим?🤔", send=True)
    chat_management(msg)


@bot.message_handler(commands=['help'])  # TODO
def command_help(msg: telebot.types.Message):
    chat_management(msg)


@bot.message_handler(commands=['chat'])
def command_chat(msg: telebot.types.Message):
    args = msg.text.split()
    if len(args) == 1:
        bot.send_message(
            msg.chat.id, "Эта команда позволяет писать <b>анонимно</b> другим людям.\n\n"
                         "<i>Использование:</i> /chat <i>chat_id</i>\n"
                         "/id - получить <i>chat_id</i> <b>любого</b> человека.\n"
                         "<b>⬇ Нажмите кнопку ниже для выбора чата ⬇</b>", "HTML",
            reply_markup=telebot.types.InlineKeyboardMarkup().add(
                telebot.types.InlineKeyboardButton(text="Выбрать чат 💬", switch_inline_query_current_chat="")))
        return
    start_chat(str(msg.chat.id), args[1])
    chat_management(msg)


@bot.message_handler(commands=['id'])
def command_id(msg: telebot.types.Message):
    users[str(msg.chat.id)]["getting_id"] = 1
    bot.send_message(msg.chat.id, "Теперь перешли мне любое сообщение из чата, "
                                  "или поделись со мной контактом этого человека.\n /cancel - отмена")
    save()
    chat_management(msg)


@bot.message_handler(commands=['d'])
def command_d(msg: telebot.types.Message):
    file_id = get_voice_id(msg)
    if file_id is None:
        bot.send_message(msg.chat.id,
                         "<b>Ответьте на голосовое/видео сообщение командой /d, чтобы его расшифровать.</b>", 'HTML')
        return
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
    chat_management(msg)


def chat_management(msg: telebot.types.Message):
    if msg.content_type in ["group_chat_created", "supergroup_chat_created", "channel_chat_created"]:
        new_group_cr(msg.chat)
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
    elif str(msg.chat.id) not in ignore:  # copy messages to admin
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


@bot.message_handler(content_types=content_types)
def chatting(msg: telebot.types.Message):
    current = str(n(msg.text) + n(msg.caption)).lower()
    args = re.split(r'[ ,.;&!?\[\]]+', current)
    chat_management(msg)
    # voter
    if msg.content_type == "poll":
        bot.send_message(msg.chat.id, random.choice(msg.poll.options).text, reply_to_message_id=msg.id)
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
        bot.send_message(msg.chat.id, "<b>Этому человеку невозможно написать через Козловского.</b>"
                                      "<i>(" + str(err.description) + ")</i>", 'HTML')
    if users[str(msg.chat.id)].pop("getting_id", 0) != 0:
        markup = telebot.types.InlineKeyboardMarkup()
        if msg.content_type == 'contact':
            user_id = str(msg.contact.user_id)
            if user_id == "None":
                bot.send_message(msg.chat.id, "Этого человека нет в Telegram.")
            else:
                markup.add(telebot.types.InlineKeyboardButton(text="Начать чат", callback_data="btn_chat_" + user_id))
                bot.send_message(msg.chat.id, user_id, reply_markup=markup)
            return
        elif msg.forward_from is not None:
            chat_id = str(msg.forward_from.id)
            markup.add(telebot.types.InlineKeyboardButton(text="Начать чат", callback_data="btn_chat_" + chat_id))
            bot.send_message(msg.chat.id, chat_id, reply_markup=markup)
            return
        save()

    # fun
    if str(msg.chat.id) not in chat_id_my:
        # image search
        if any(s in current for s in searches):
            if msg.content_type == 'photo':
                photo_search(msg.chat.id, msg.id, msg.photo[-1])
                return
            elif msg.reply_to_message.content_type == 'photo':
                photo_search(msg.chat.id, msg.id, msg.reply_to_message.photo[-1])
                return
        # goroda game
        try:
            index = active_goroda.index(str(msg.chat.id))
            if any(s in args for s in ends):
                active_goroda.pop(index)
                current_letters.pop(index)
                bot.send_message(msg.chat.id, "<b>Конец игры</b>", "HTML")
                save()
                return
            if current:
                if current[0] == current_letters[index] or current_letters[index] == "":
                    try:
                        random_city = random.choice(goroda[get_city_letter(current)])
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
        ai_talk(n(msg.text) + n(msg.caption), str(msg.chat.id), msg.chat.type == 'private', args, msg_voice=msg)


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
    index = 0
    for u in users:
        index += 1
        results.append(telebot.types.InlineQueryResultArticle(
            index, users[u]['name'], telebot.types.InputTextMessageContent("/chat " + u),
            description=users[u]['desc'] + "\nНажмите, чтобы написать в " + (
                "этот чат" if users[u]['private'] else "эту группу"), thumb_url=users[u].get('photo_url')))
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


# Запуск бота
Thread(target=timer).start()
print("start")
bot.infinity_polling(timeout=60, long_polling_timeout=60)
