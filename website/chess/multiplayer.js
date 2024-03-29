export function Multiplayer(msg_handler, init_handler, opponent) {
    let answer = dict => msg_handler({data: dict})
    let game, import_task = loadChessJS();
    let color, ws;

    let connectWebSocket = () => {
        ws = new WebSocket(
            `wss://${window.location.host}/cmp?oid=${opponent}&data=${encodeURIComponent(Telegram.WebApp.initData)}`)
        ws.onopen = e => {
            console.log(e)
        }
        ws.onclose = e => {
            console.log(e)
            if (e.reason) {
                Telegram.WebApp.showAlert(e.reason)
                Telegram.WebApp.close()
            } else if (!window.navigator.onLine) {
                Telegram.WebApp.showAlert("Нет подключения к интернету 😢")
                window.ononline = connectWebSocket
            } else
                setTimeout(connectWebSocket, 800);
            answer({cmd: 'reconnect'})
        }
        ws.onmessage = e => {
            console.log(e)
            let msg = JSON.parse(e.data)
            switch (msg.cmd) {
                case 'init':
                    document.getElementById("op-name").innerText = msg.name

                    let avaEl = document.getElementById("op-avatar")
                    if (msg.photo_id === null) {
                        avaEl.innerText = msg.name[0]
                        avaEl.style.removeProperty('background-image')
                    } else
                        avaEl.style.backgroundImage = `url(../p/${msg.photo_id}.jpg)`

                    import_task.then(() => {
                        game = new Chess(msg.fen)
                        color = msg.color
                        init_handler(msg.fen, color) // ready to init DOM
                    })

                    if (msg.restart) wantRestart()

                    answer({cmd: 'online', online: msg.online})
                    break
                case 'move':
                    game.load(msg.fen)
                    answer({
                        cmd: 'snapEnd', // opponent made move
                        fen: msg.fen
                    })
                    break
                case 'online':
                    answer({cmd: 'online', online: msg.online})
                    break
                case 'wantRestart':
                    wantRestart()
                    break
                case 'restart':
                    game.reset()
                    color = color === 'w' ? 'b' : 'w'
                    answer({cmd: 'restart', color: color})
                    break
            }
        }
    }
    let wantRestart = () => Telegram.WebApp.showPopup({
        title: 'Начать новую партию', message: 'Соперник хочет начать эту партию сначала', buttons:
            [{id: 'restart', type: 'destructive', text: 'Разрешить'}, {id: 'reject', type: 'cancel'}]
    })

    connectWebSocket()

    return {
        postMessage(d) {
            switch (d.cmd) {
                case 'move':
                    let move = game.move({
                        from: d.source,
                        to: d.target,
                        promotion: 'q'
                    });
                    if (move === null)
                        answer({
                            cmd: d.cmd,
                            action: 'snapback'
                        })
                    else {
                        let fen = game.fen()
                        answer({
                            cmd: d.cmd,
                            action: 'drop',
                            target: d.target,
                            history: game.history(),
                            fen: fen
                        })
                        console.log(move)
                        ws.send(JSON.stringify({cmd: 'move', san: move.san}))
                    }
                    break
                case 'status':
                    let title = 'Ничья';
                    let description;
                    let status;
                    let type = 'end';
                    let is_check;
                    if (game.in_checkmate()) {
                        is_check = true
                        title = game.turn() === 'w' ? 'Мат белым' : 'Мат чёрным';
                        description = game.turn() === color ? 'Вы проиграли' : 'Вы выиграли'
                        status = `Мат • ${(d.color === 'b' ? 'Белые' : 'Чёрные') + ' победили'}`;
                    } else if (game.insufficient_material())
                        description = 'Невозможно поставить мат'
                    else if (game.in_threefold_repetition())
                        description = 'Троекратное повторение позиции'
                    else if (game.in_stalemate())
                        description = 'Пат'
                    else if (game.in_draw())
                        description = 'Правило 50 ходов'
                    else if (game.in_check()) {
                        is_check = true
                        type = 'check'
                    } else type = ''

                    if (title === 'Ничья') status = `Ничья • ${description}`;
                    answer({
                        cmd: d.cmd,
                        type: type,
                        title: title,
                        desc: description,
                        status: status,
                        turn: game.turn(),
                        sq: is_check ? game.king_sq(game.turn()) : null
                    })
                    break
                case 'moves':
                    let moves = game.moves({
                        square: d.square,
                        verbose: true
                    });
                    answer({
                        cmd: d.cmd,
                        moves: moves,
                        square: d.square
                    })
                    break
                case 'reject':
                    ws.send(JSON.stringify({cmd: 'reject'}))
                    break
                case 'restart':
                    ws.send(JSON.stringify({cmd: 'restart'}))
                    break
            }
        }
    }
}

let loadChessJS = () => {
    return new Promise(resolve => {
        const scriptEle = document.createElement("script");
        scriptEle.async = true;
        scriptEle.src = './lib/chess.min.js';

        scriptEle.onload = () => resolve();

        document.body.appendChild(scriptEle);
    });
};