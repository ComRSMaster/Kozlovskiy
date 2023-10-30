# modified version of https://github.com/Soulter/hugging-chat-api/blob/master/src/hugchat/hugchat.py
from asyncio import ensure_future

import ujson
from aiohttp import ClientSession, ClientError
import uuid

from ujson import JSONDecodeError


class HuggingChat:
    cookies: dict
    """Cookies for authentication"""

    session: ClientSession
    """HuggingChat session"""

    def __init__(self, cookies: dict) -> None:

        self.cookies = cookies

        self.json_header = {"Content-Type": "application/json"}

        self.session = ClientSession("https://huggingface.co", json_serialize=ujson.dumps)
        # set cookies

        self.conversation_id_list = []
        self.__not_summarize_cids = []
        self.current_conversation = ''

    def __del__(self):
        ensure_future(self.session.close())

    def get_headers(self, ref=True, ref_cid=None) -> dict:
        _h = {
            "Accept": "*/*",
            "Connection": "keep-alive",
            "Host": "huggingface.co",
            "Origin": "https://huggingface.co",
            "Referer": "https://huggingface.co/chat",
            "Sec-Fetch-Site": "same-origin",
            "Content-Type": "application/json",
            "Sec-Ch-Ua-Platform": "Windows",
            "Sec-Ch-Ua": "Chromium\";v=\"116\", \"Not)A;Brand\";v=\"24\", \"Microsoft Edge\";v=\"116",
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/112.0.0.0 Safari/537.36",
        }
        if ref:
            if ref_cid is None:
                ref_cid = self.current_conversation
            _h["Referer"] = f"https://huggingface.co/chat/conversation/{ref_cid}"
        return _h

    async def new_conversation(self) -> str:
        """
        Create a new conversation. Return the new conversation id.
        You should change the conversation by calling change_conversation() after calling this method.
        """
        err_count = 0

        # Accept the welcome modal when init.
        # 17/5/2023: This is not required anymore.
        # if not self.accepted_welcome_modal:
        #     self.accept_ethics_modal()

        # Create new conversation and get a conversation id.

        _header = self.get_headers(ref=False)

        while True:
            try:
                async with self.session.post("/chat/conversation", json={"model": "meta-llama/Llama-2-70b-chat-hf"},
                                             headers=_header, cookies=self.cookies) as resp:
                    cid = (await resp.json(loads=ujson.loads))['conversationId']
                    self.conversation_id_list.append(cid)
                    self.__not_summarize_cids.append(cid)  # For the 1st chat, the conversation needs to be summarized.
                    await self.__preserve_context(cid, "1_1")
                    return cid

            except (ClientError, JSONDecodeError):
                err_count += 1
                if err_count > 5:
                    raise Exception(f"Failed to create new conversation.")
                continue

    def change_conversation(self, conversation_id: str):
        """
        Change the current conversation to another one. Need a valid conversation id.
        """
        self.current_conversation = conversation_id

    async def summarize_conversation(self, conversation_id: str = None) -> str:
        """
        Return a summary of the conversation.
        """
        if conversation_id is None:
            conversation_id = self.current_conversation

        async with self.session.post(f"/chat/conversation/{conversation_id}/summarize", headers=self.get_headers(),
                                     cookies=self.cookies) as r:

            if r.status != 200:
                raise Exception(f"Failed to send chat message with status code: {r.status}")

            response = await r.json()
            if 'title' in response:
                return response['title']

            raise Exception(f"Unknown server response: {response}")

    async def delete_conversation(self, conversation_id: str):
        """
        Delete a HuggingChat conversation by conversation_id.
        """
        async with self.session.delete(f"/chat/conversation/{conversation_id}", headers=self.get_headers(),
                                       cookies=self.cookies) as r:
            if r.status != 200:
                raise Exception(f"Failed to delete conversation with status code: {r.status}")

    async def check_operation(self) -> bool:
        async with self.session.post(
                f"/chat/conversation/{self.current_conversation}/__data.json?x-sveltekit-invalidated=1_1",
                headers=self.get_headers(), cookies=self.cookies) as r:
            return r.status == 200

    async def chat(
            self,
            text: str,
            temperature: float = 0.4,
            top_p: float = 0.95,
            repetition_penalty: float = 1.2,
            top_k: int = 50,
            truncate: int = 1024,
            watermark: bool = False,
            max_new_tokens: int = 1024,
            stop: list = None,
            return_full_text: bool = False,
            stream: bool = True,
            use_cache: bool = False,
            is_retry: bool = False,
            retry_count: int = 5,
            cooldown: int = 0,
    ):
        """
        Send a message to the current conversation. Return the response text.
        You can customize these optional parameters.
        You can turn on the web search by set the parameter `web_search` to True
        """

        if stop is None:
            stop = ["</s>"]

        if self.current_conversation == '':
            self.current_conversation = await self.new_conversation()

        req_json = {
            "inputs": text,
            "parameters": {
                "temperature": temperature,
                "top_p": top_p,
                "repetition_penalty": repetition_penalty,
                "top_k": top_k,
                "truncate": truncate,
                "watermark": watermark,
                "max_new_tokens": max_new_tokens,
                "stop": stop,
                "return_full_text": return_full_text,
                "stream": stream,
            },
            "options": {
                "use_cache": use_cache,
                "is_retry": is_retry,
                "id": str(uuid.uuid4()),
            },
            "stream": True,
        }

        current_cooldown = 0
        while retry_count > 0:
            async with self.session.post(f"/chat/conversation/{self.current_conversation}",
                                         json=req_json, headers=self.get_headers(), cookies=self.cookies) as resp:
                res_text = ""

                if resp.status != 200:
                    retry_count -= 1
                    if retry_count <= 0:
                        raise Exception(f"Код ошибки: {resp.status}")

                async for line in resp.content:
                    line = line[:-1]  # remove trailing \n
                    if not line:
                        continue

                    res = line.decode("utf-8")

                    try:
                        obj = ujson.loads(res[5:])
                    except JSONDecodeError:
                        if '{"error":"Model is overloaded"' in res:
                            raise Exception("Сервер перегружен. Попробуйте позже")
                        raise Exception(f"Ошибка: не удалось распознать ответ от сервера ({res})")

                    if "generated_text" in obj:
                        if obj["token"]["text"].endswith("</s>"):
                            res_text += obj["token"]["text"][:-5]
                            yield res_text
                        else:
                            res_text += obj["token"]["text"]

                            if current_cooldown <= cooldown:
                                yield res_text
                                current_cooldown = cooldown
                            else:
                                current_cooldown -= 1

                    elif "error" in obj:
                        raise Exception(f"Ошибка: {obj['error']}")
            # try to summarize the conversation and preserve the context.
            # noinspection PyBroadException
            try:
                if self.current_conversation in self.__not_summarize_cids:
                    await self.summarize_conversation()
                    self.__not_summarize_cids.remove(self.current_conversation)
                await self.__preserve_context(ref_cid=self.current_conversation)
            except Exception:
                pass

            return

    async def __preserve_context(self, cid: str = None, ending: str = "1_", ref_cid: str = None):
        if cid is None:
            cid = self.current_conversation

        async with self.session.get(f"/chat/conversation/{cid}/__data.json?x-sveltekit-invalidated={ending}",
                                    cookies=self.cookies, headers=self.get_headers(ref_cid=ref_cid), data={}) as resp:
            if resp.status == 200:
                return {'message': "Context Successfully Preserved", "status": 200}
            else:
                return {'message': "Internal Error", "status": 500}


async def test():
    bot = HuggingChat({'hf-chat': 'token'})
    async for m in bot.chat("Привет", max_new_tokens=5):
        print(m)

# chat.change_conversation(conv_id)
#
# if chat_id:
#     ensure_future(bot.send_chat_action(chat_id, 'typing'))
#
# print(query)
#
# result = ''
# async for text in chat.chat(query, cooldown=15):  # 15 токенов за сообщение
#     print(text)
#
#     if chat_id:
#         markup = reply_markups[chat_id] if is_init_msg else None
#         try:
#             if msg_id is None:
#                 msg_id = (await bot.send_message(chat_id, text, reply_markup=markup)).id
#                 ensure_future(bot.send_chat_action(chat_id, 'typing'))
#             else:
#                 await bot.edit_message_text(text, chat_id, msg_id, reply_markup=markup)
#         except ApiTelegramException:
#             continue
#     result = text
#
# return result

# async with aiohttp.ClientSession('https://api.together.xyz', json_serialize=ujson.dumps) as session:
#     if config.together_token is None:
#         async with session.get('/bloom-chat') as response:
#             config.together_token = response.cookies['together.session-token']
#     print(config.together_token)
# async with session.post(
#         '/api/inference',
#         json={"max_tokens": 512, "stop": ["<human>", "</s>"], "top_p": 1, "top_k": 40,
#               "repetition_penalty": 1.1, "temperature": 0.6,
#               "model": "sambanovasystems/BLOOMChat-176B-v1",
#               "prompt": talks[chat_id][-2],
#               "prompt_format_string":
#                   "\n<human>: Привет!\n<bot>: Привет! Я - российский актёр Даня Козловский. Я сегодня "
#                   "снимаю новый фильм, который должен стать самым высокобюджетным в истории. "
#                   'Мои фильмы - "На районе", "Чернобыль", "Духless 2", "13 клиническая". Я здесь, '
#                   "чтобы помочь вам с вашими вопросами и дать точные, уважительные и исчерпывающие ответы. Я "
#                   "постараюсь изо всех сил отвечать на ваши вопросы на русском языке."
#                   "\n<human>: {prompt}\n<bot>:",
#               "stream_tokens": True, "repetitive_penalty": 1},
#         cookies={'together.session-token': config.together_token}) as rec:
#
#     text = ''
#     edit_cooldown = 0
#     async for line in rec.content:
#         line = line[:-1]
#         if not line:
#             continue
#
#         data = line[6:]
#         if data == b'[DONE]':
#             edit_cooldown = 0
#         else:
#             text += ujson.decode(data)['choices'][0]['text']
#
#         if edit_cooldown <= 0:
#             edit_cooldown = 20  # 20 токенов за сообщение
#             if chat_id:
#                 if chat_id not in talks:
#                     return
#                 talks[chat_id][index] = text
#
#                 markup = reply_markups[chat_id] if is_init_msg else None
#                 if msg_id is None:
#                     try:
#                         msg_id = (await bot.send_message(chat_id, text, reply_markup=markup)).id
#                         await bot.send_chat_action(chat_id, 'typing')
#                     except ApiTelegramException:
#                         continue
#                 else:
#                     try:
#                         await bot.edit_message_text(text, chat_id, msg_id, reply_markup=markup)
#                     except ApiTelegramException:
#                         pass
#         edit_cooldown -= 1
#     config.together_token = rec.cookies['together.session-token']
#
#     return text


if __name__ == "__main__":
    import asyncio

    asyncio.run(test())
