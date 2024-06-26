from aiohttp import web

from helpers import session_manager
from helpers.bot import bot
from helpers.db import BotDB
from pathlib import Path

routes = web.RouteTableDef()

static_dir_path = Path('website')


@web.middleware
async def static_serve(request, handler):
    relative_file_path = Path(request.path).relative_to('/')  # remove root '/'
    file_path = static_dir_path / relative_file_path  # rebase into static dir
    if not file_path.exists():
        return web.HTTPNotFound()
    if file_path.is_dir():
        file_path /= 'index.html'
        if not file_path.exists():
            return web.HTTPNotFound()
    return web.FileResponse(file_path)


async def shutdown(app):
    await bot.close_session()

    if BotDB.pool is not None:
        await BotDB.pool.clear()

    await session_manager.close_all_sessions()
    print("server stopped")


async def app_factory():
    app = web.Application(middlewares=[static_serve])
    app.add_routes(routes)
    app.on_shutdown.append(shutdown)
    return app
