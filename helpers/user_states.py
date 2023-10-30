from telebot.asyncio_filters import AdvancedCustomFilter


class States:
    CHATTING = 1
    AI_TALK = 2
    CASINO = 3
    CITIES = 4
    GETTING_ID = 5
    BALANCE = 6
    UP_PHOTO = 7
    WAIT_GEO = 8


class UserStateFilter(AdvancedCustomFilter):
    key = 'state'

    async def check(self, msg, state):
        # msg.state driven from middleware handler
        return state == msg.state
