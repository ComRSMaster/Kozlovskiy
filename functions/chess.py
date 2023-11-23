from dataclasses import dataclass
from urllib.parse import quote

from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from starlette.websockets import WebSocket, WebSocketState
from telebot.types import Message, WebAppInfo
from telebot.util import quick_markup, parse_web_app_data

from helpers.bot import bot
from helpers.config import web_url, bot_token
from helpers.db import BotDB
import chess


@dataclass(repr=False, eq=False)
class ChessGame:
    board: chess.Board
    player_white: int
    player_black: int


ws: dict[int, WebSocket] = {}
games: dict[int, ChessGame] = {}
chess_url = 'https://t.me/Kkoslovsskiy27_bot/chess_kozlo'


@bot.message_handler(['chess'])
async def command_help(msg: Message):
    await bot.send_message(msg.chat.id, 'Шахматы ⬇', reply_markup=quick_markup({
        'Играть с ботом': {'web_app': WebAppInfo(web_url + 'chess/chess.html')} if msg.chat.type == 'private'
        else {'url': chess_url},
        'Мои партии': {'url': f'{chess_url}?startapp=me'},
        'С друзьями': {
            'url': f"https://t.me/share/url?url={chess_url}%3Fstartapp%3D{msg.from_user.id}&text="
                   f"Играть в шахматы против {quote(msg.from_user.full_name)}"}
    }, 1))


async def chess_mp_endpoint(websocket: WebSocket):
    data = parse_web_app_data(bot_token, websocket.query_params['data'])

    if not data:
        await websocket.close(reason="Data is invalid")
        return

    mid = data['user']['id']
    oid = int(websocket.query_params['oid'])

    if player_is_online(mid):
        await ws[mid].close(reason='Вы открыли шахматы на другом устройстве')
    ws[mid] = websocket

    my_name = (data['user']['first_name'] + ' ' + data['user']['last_name']).rstrip()

    chess_data = await BotDB.fetchone(
        "SELECT `id`, `fen`, `player_white`, `player_black`, `status` FROM `chess`"
        "WHERE (`player_black` = %(mid)s AND `player_white` = %(oid)s) OR"
        "(`player_white` = %(mid)s AND `player_black` = %(oid)s);"
        "INSERT INTO `users` (`id`, `name`, `is_private`, `only_chess`) VALUES (%(mid)s, %(name)s, 1, 1) AS new "
        "ON DUPLICATE KEY UPDATE `name` = new.`name`",
        {'name': my_name, 'mid': mid, 'oid': oid})
    opp_user = await BotDB.fetchone("SELECT `name`, `photo_id` FROM `users` WHERE `id` = %s", oid)

    if chess_data is None:
        fen = chess.STARTING_FEN
        player_white = mid
        player_black = oid
        status = 0

        game_id = await BotDB.autoincrement(
            "INSERT INTO `chess` SET `player_white` = %s, `player_black` = %s, `fen` = %s",
            (mid, oid, fen))
    else:
        game_id, fen, player_white, player_black, status = chess_data

    if opp_user is None:
        opp_user = 'Игрок', None

    await websocket.accept()
    await websocket.send_json({'cmd': 'init', 'fen': fen, 'color': 'w' if player_white == mid else 'b',
                               'online': player_is_online(oid), 'name': opp_user[0], 'photo_id': opp_user[1],
                               'restart': status == oid})

    if game_id in games:
        game = games[game_id]
    else:
        game = games[game_id] = ChessGame(chess.Board(fen), player_white, player_black)

    if player_is_online(oid):
        await ws[oid].send_json({'cmd': 'online', 'online': True})

    async for msg in websocket.iter_json():
        if msg['cmd'] == 'move':
            try:
                if mid == game.player_white ^ game.board.turn:
                    raise ValueError  # if the player tries to hack game and move as another color.

                game.board.push_san(msg['san'])

            except (ValueError, KeyError):
                await websocket.close(reason="Неправильный ход")
                return

            fen = game.board.fen()
            if player_is_online(oid):
                await ws[oid].send_json({'cmd': 'move', 'fen': fen})

            elif not (await BotDB.fetchone("SELECT `only_chess` FROM `users` WHERE `id` = %s", oid)):
                # not only chess user
                info = '<b>мат</b>' if game.board.is_checkmate() else '<b>шах</b>' if game.board.is_check() else None
                await bot.send_message(
                    oid, f"Игрок <b>{my_name}</b> сделал ход в шахматах{' и поставил вам ' + info if info else ''}",
                    reply_markup=quick_markup({
                        'Продолжить партию': {'url': f'{chess_url}?startapp={mid}'}}))

            await BotDB.execute("UPDATE `chess` SET `fen` = %s WHERE `id` = %s", (fen, game_id))

        elif msg['cmd'] == 'restart':
            status, = await BotDB.fetchone("SELECT `status` FROM `chess` WHERE `id` = %s", game_id)

            if status == oid or game.board.is_game_over(claim_draw=True) and mid == game.player_black ^ game.board.turn:

                game.player_white, game.player_black = game.player_black, game.player_white
                game.board.reset()

                await websocket.send_json({'cmd': 'restart'})
                if player_is_online(oid):
                    await ws[oid].send_json({'cmd': 'restart'})

                await BotDB.execute(
                    "UPDATE chess SET fen = %s, status = 0, player_white = %s, player_black = %s WHERE `id` = %s",
                    (chess.STARTING_FEN, game.player_white, game.player_black, game_id))

            elif status == 0:
                if player_is_online(oid):
                    await ws[oid].send_json({'cmd': 'wantRestart'})
                await BotDB.execute(
                    "UPDATE `chess` SET `status` = %s WHERE `id` = %s", (mid, game_id))

        elif msg['cmd'] == 'reject':
            await BotDB.execute("UPDATE `chess` SET `status` = 0 WHERE `id` = %s", game_id)

    if player_is_online(oid):
        await ws[oid].send_json({'cmd': 'online', 'online': False})
    else:
        del games[game_id]

    ws.pop(mid, 0)


async def get_chess_games(request: Request):
    data = parse_web_app_data(bot_token, request.query_params['data'])
    if not data:
        return Response(status_code=401)
    data2 = await BotDB.fetchall(
        "SELECT `fen`, (users.`id` = `player_black`), users.`id`, `name`, `photo_id` FROM `chess`"
        "JOIN `users` ON (users.`id` = `player_white` AND `player_black` = %(mid)s) OR"
        "(users.`id` = `player_black` AND `player_white` = %(mid)s)", {'mid': data['user']['id']})

    return JSONResponse(data2)


def player_is_online(player_id):
    return (player_id in ws) and ws[player_id].application_state == WebSocketState.CONNECTED \
        and ws[player_id].client_state == WebSocketState.CONNECTED
