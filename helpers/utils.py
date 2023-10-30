import asyncio
import re

from telebot import types
from telebot.util import escape

from helpers.bot import bot
from helpers.config import ends


def n(text: str, addition=''):
    """Если text - None, то вернуть пустую строку"""
    return "" if text is None else addition + text


def bool_emoji(condition: bool):
    """Превращает True/False в ✅/❌"""
    return '✅' if condition else '❌'


async def send_status_periodic(chat_id, status):
    while True:
        await bot.send_chat_action(chat_id, status)
        await asyncio.sleep(5)


def nlp_stop(msg: str):
    args = re.split(r'[ ,.;&!?\[\]]+', msg.lower(), maxsplit=3)

    return any(s in args for s in ends)


def user_link(user: types.User, include_id: bool = False) -> str:
    """
    Function from "telebot.util", but <code> formatting, instead of <pre>.

    Returns an HTML user link. This is useful for reports.
    Attention: Don't forget to set parse_mode to 'HTML'!


    .. code-block:: python3
        :caption: Example:

        bot.send_message(your_user_id, user_link(message.from_user) + ' started the bot!', parse_mode='HTML')

    .. note::
        You can use formatting.* for all other formatting options(bold, italic, links, and etc.)
        This method is kept for backward compatibility, and it is recommended to use formatting.* for
        more options.

    :param user: the user (not the user_id)
    :type user: :obj:`telebot.types.User`

    :param include_id: include the user_id
    :type include_id: :obj:`bool`

    :return: HTML user link
    :rtype: :obj:`str`
    """
    name = escape(user.first_name)
    return (f"<a href='tg://user?id={user.id}'>{name}</a>"
            + (f" (<code>{user.id}</code>)" if include_id else ""))