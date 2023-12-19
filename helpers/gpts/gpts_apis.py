import os
import time
import uuid

import aiohttp
import ujson
from telebot.async_telebot import logger

from helpers.session_manager import auto_close
import ssl

SYSTEM_PROMPT = {"role": "system",
                 "content": '''Ты - российский актёр Даня Козловский.
Ты уже снял фильмы: "На районе", "Чернобыль", "Духless 2", "13 клиническая".'''}


def error_handler(status_code, error_text):
    if status_code == 503:
        return "Сервер OpenAI сейчас перегружен. Попробуйте позже."

    elif status_code == 401:
        logger.error("Токен ChatGPT не работает")
        return "На данный момент ChatGPT недоступен. Попробуйте позже."

    error = f"Код ошибки: {status_code}\n```\n{error_text[4000:]}\n```"
    logger.error(error)
    return error


class ChatGPT:
    def __init__(self, openai_key):
        self.session = auto_close(aiohttp.ClientSession(
            "https://ai.fakeopen.com",
            headers={"Authorization": f"Bearer {openai_key}"},
            json_serialize=ujson.dumps))

    async def chat(self, messages, cooldown=0):
        async with self.session.post(url="/v1/chat/completions", json={
            "model": "gpt-3.5-turbo",
            "messages": [SYSTEM_PROMPT, *messages],
            "stream": True
        }) as response:
            if response.status != 200:
                yield error_handler(response.status, await response.text())
                return
            text_buffer = ''
            current_cooldown = 0

            async for line in response.content:
                if line and line.startswith(b"data:"):
                    # print(line)
                    line = line[6:-1]  # remove "data: " prefix and "\n" suffix
                    if line.strip() == b"[DONE]":
                        if text_buffer:
                            yield text_buffer
                        return
                    else:
                        msg = ujson.loads(line.decode("utf-8"))['choices'][0]
                        if msg['finish_reason'] is not None:
                            if text_buffer:
                                yield text_buffer
                            return

                        content = msg['delta']['content']

                        if content:
                            text_buffer += content

                            current_cooldown -= 1
                            if current_cooldown <= 0:
                                current_cooldown = cooldown
                                yield text_buffer
                                text_buffer = ''


class GigaChat:
    def __init__(self, gigachat_secret):
        ssl_ctx = ssl.create_default_context(
            cafile=os.path.dirname(__file__) + '/gigachat_crt/russian_trusted_root_ca_pem.crt')
        conn = aiohttp.TCPConnector(ssl_context=ssl_ctx)

        self.token_expires_at = 0
        self.access_token: str = ''

        self.session = auto_close(aiohttp.ClientSession(json_serialize=ujson.dumps, connector=conn))
        self.gigachat_secret = gigachat_secret

    async def chat(self, messages, cooldown=0):
        # если до истечения действия токена осталось менее 1 минуты
        if self.token_expires_at - int(time.time() * 1000) < 60000:
            await self.new_access_token()

        async with self.session.post(url="https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
                                     headers={"Authorization": f"Bearer {self.access_token}"},
                                     json={
                                         "model": "GigaChat:latest",
                                         "messages": [SYSTEM_PROMPT, *messages],
                                         "stream": True,
                                         "update_interval": cooldown * 0.1
                                     }) as response:
            if response.status != 200:
                error = f"Код ошибки: {response.status}\n{await response.text()}"
                logger.error(error)
                yield error
                return

            async for line in response.content:
                # print(line)
                if line and line.startswith(b"data:"):
                    line = line[6:-1]  # remove "data: " prefix and "\n" suffix
                    if line.strip() == b"[DONE]":
                        return
                    else:
                        msg = ujson.loads(line.decode("utf-8"))['choices'][0]
                        # print(msg)
                        content = msg['delta']['content']

                        if content:
                            yield content

                        if 'finish_reason' in msg:
                            return

    async def new_access_token(self):
        async with self.session.post(url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
                                     headers={"Authorization": f"Bearer {self.gigachat_secret}",
                                              "RqUID": str(uuid.uuid4()),
                                              "Content-Type": "application/x-www-form-urlencoded"},
                                     data={"scope": "GIGACHAT_API_PERS"}) as response:
            data = await response.json()
        print(data)
        self.access_token = data['access_token']
        self.token_expires_at = data['expires_at']


async def test_chatgpt():
    import os

    chatgpt = ChatGPT(os.getenv("openai_key"))

    async for m in chatgpt.chat([{
        "role": "user",
        "content": "Привет, чем занят?"
    }]):
        print(m, end='')

    await chatgpt.session.close()


async def test_gigachat():
    print('init')
    gigachat = GigaChat(
        "OGYwOTgxOTItNWYwZS00ZWJmLWJlZGUtYjVjOWMwNDY5ZTU4OjEzNzUzZGI5LTYyZGEtNDM1ZS05NTJlLWZiMGNhODdjYmVkMQ==")

    async for m in gigachat.chat([{
        "role": "user",
        "content": "Как написать змейку на python?"
    }]):
        print(m, end='')

    await gigachat.session.close()


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_gigachat())
