from aiohttp import ClientSession

sessions: list[ClientSession] = []


def auto_close(session: ClientSession) -> ClientSession:
    sessions.append(session)
    return session


async def close_all_sessions():
    for session in sessions:
        await session.close()
