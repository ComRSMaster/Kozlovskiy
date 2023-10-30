let board, ai, searchDepth = 3, is_bot = false, is_inited = false;

// DOM elements
let gameStatus = document.getElementById('game-status'),
    undoBtn = document.getElementById('undo-btn'),
    redoBtn = document.getElementById('redo-btn'),
    historyLine = document.getElementById('hist-line'),
    historyNavbar = document.getElementById('hist-nav'),
    onlineCircle = document.getElementById('online-circle'),
    settingBtn = document.getElementById('settings-btn'),
    mpLoading = document.getElementById('mp-loading')

let myColor; // color ('w' or 'b')

let msg_handler = e => {
    let d = e.data;
    switch (d.cmd) {
        case 'move':
            if (d.action === 'snapback') {
                board.snapbackDraggedPiece()
                return
            }
            board.dropDraggedPieceOnSquare(d.target, d.fen)

            undoBtn.disabled = false
            redoBtn.disabled = true

            ai.postMessage({cmd: 'status'});
            renderMoveHistory(d.history);
            // AI move (stub in multiplayer)
            ai.postMessage({cmd: 'ai', depth: searchDepth});

            if (is_bot) window.localStorage.setItem('fen', d.fen)

            break
        case 'snapEnd': // AI or opponent player turn ends
            board.position(d.fen)
            ai.postMessage({cmd: 'status'});

            if (is_bot) {
                renderMoveHistory(d.history);
                window.localStorage.setItem('fen', d.fen)
            }

            break
        case 'status':
            if (d.type === 'end') {
                Telegram.WebApp.showPopup({
                    title: d.title, message: d.desc, buttons:
                        [{id: 'restart', type: 'destructive', text: 'Начать новую партию'}, {type: 'close'}]
                })
                gameStatus.innerText = d.status
                undoBtn.disabled = true

                board.config.draggable = false
            } else
                gameStatus.innerText = d.turn === myColor ? 'Ваш ход' : 'Ожидание соперника'
            if (d.sq) board.setCheck(d.sq) // check or checkmate
            break
        case 'moves':
            for (let i = 0; i < d.moves.length; i++)
                board.addCircle(d.moves[i].to)
            break
        case 'online': // only for multiplayer
            if (d.online) {
                onlineCircle.hidden = false
                onlineCircle.animate({transform: ['scale(0)', 'scale(1)']},
                    {duration: 200, easing: 'ease', fill: "forwards"})
            } else {
                onlineCircle.animate({transform: ['scale(1)', 'scale(0)']},
                    {duration: 200, easing: 'ease-in', fill: "forwards"})
                    .onfinish = () => onlineCircle.hidden = true
            }
            break
        // undo / redo (stub in multiplayer)
        case 'undo':
            if (d.do) {
                redoBtn.disabled = false
                board.position(d.fen)
                renderMoveHistory(d.history)
                ai.postMessage({cmd: 'status'})
                window.localStorage.setItem('fen', d.fen)
            } else undoBtn.disabled = true
            break
        case 'redo':
            if (d.do) {
                undoBtn.disabled = false
                board.position(d.fen)
                renderMoveHistory(d.history)
                ai.postMessage({cmd: 'status'})
                window.localStorage.setItem('fen', d.fen)
            } else redoBtn.disabled = true
            break
        case 'pos': // move if current move is AI
            if (d.white) return;
            ai.postMessage({cmd: 'ai', depth: searchDepth});
            ai.postMessage({cmd: 'snapEnd'});
            break
        case 'restart':
            ai.postMessage({cmd: 'pos'});
            ai.postMessage({cmd: 'status'});

            renderMoveHistory([])
            undoBtn.disabled = true
            redoBtn.disabled = true
            board.config.draggable = true

            if (is_bot) {
                board.start()
                window.localStorage.removeItem('fen')
            } else {
                myColor = d.color
                board.init(null, myColor)
            }
            break
        case 'reconnect': // only for multiplayer
            gameStatus.innerText = 'Переподключение'
            mpLoading.hidden = false
            break
    }
}

function renderMoveHistory(moves) {
    historyLine.innerText = ''
    for (let i = 0; i < moves.length; i = i + 2)
        historyLine.innerHTML += `<b>${i / 2 + 1}.</b> ${moves[i]} ${moves[i + 1] ? moves[i + 1] : ' '} `

    historyLine.scrollLeft = historyLine.scrollWidth
}

let onDrop = (source, target) =>
    ai.postMessage({cmd: 'move', source: source, target: target});


let onSnapEnd = () =>
    ai.postMessage({cmd: 'snapEnd'});


let onMouseoverSquare = square =>
    ai.postMessage({cmd: 'moves', square: square});

let init = (pos, color) => {
    myColor = color
    mpLoading.hidden = true
    board.init(pos, color)
    ai.postMessage({cmd: 'status'});
}

Telegram.WebApp.onEvent('popupClosed', d => {
    let id = d.button_id;

    if (!id) return

    if (id === 'restart')
        ai.postMessage({cmd: 'restart'})

    else if (id === 'reject')
        ai.postMessage({cmd: 'reject'})

    else searchDepth = parseInt(id)
})

let make_game_name = (avatar, name, statusStr, onclick) => {
    let root = document.createElement('div')
    let img = document.createElement('div')
    let nameEl = document.createElement('span')
    let statusEl = document.createElement('span')

    img.className = "avatar me-2"
    if (avatar)
        img.style.backgroundImage = avatar
    else {
        img.style.backgroundColor = 'var(--tg-theme-bg-color)'
        img.innerText = name[0]
    }

    nameEl.innerText = name

    statusEl.className = "secondary"
    statusEl.innerText = statusStr

    root.appendChild(img)
    root.appendChild(nameEl)
    root.appendChild(statusEl)
    root.onclick = onclick

    return root
};

let init_ai = () => {
    is_inited = true;
    is_bot = true

    ai = new Worker("ai.js");
    ai.onmessage = msg_handler
    undoBtn.hidden = false
    redoBtn.hidden = false
    historyNavbar.hidden = false
    settingBtn.style.display = 'inherit'
    onlineCircle.hidden = false

    let fen = window.localStorage.getItem('fen')
    ai.postMessage({cmd: 'pos', fen: fen})
    init(fen, 'w')
}

let init_mp = opponent => {
    is_inited = true;
    gameStatus.innerText = 'Подключение'
    mpLoading.hidden = false
    import('./multiplayer.js').then(obj =>
        ai = obj.Multiplayer(msg_handler, init, opponent))
}

let data = Telegram.WebApp.initDataUnsafe

board = Chessboard('board', {
    draggable: true,
    onDrop: onDrop,
    onMouseoverSquare: onMouseoverSquare,
    onSnapEnd: onSnapEnd
});

let start_param = data['start_param'];
if (!start_param) { // play with bot
    init_ai()
} else if (start_param === 'me' || parseInt(start_param) === data['user']['id']) { // show games
    let modal = document.getElementById("myModal")
    let modalContainer = document.getElementById("modal-container")
    let myGames = document.getElementById("my-games")

    let closeModal = () => {
        modal.animate(
            {backgroundColor: 'rgba(0, 0, 0, 0)'},
            {duration: 400, easing: "ease-in-out"})
        modalContainer.animate(
            {transform: 'translate(0, 100%)'},
            {duration: 400, easing: "ease-in-out"}
        ).onfinish = () => {
            modal.style.display = "none"
        }
        if (!is_inited) init_ai()
    }
    let closeBtn = document.getElementsByClassName("close")[0]
    modal.style.display = "block"

    closeBtn.onclick = () => closeModal()

    window.onclick = e => {
        if (e.target === modal) closeModal()
    }
    myGames.appendChild(make_game_name("url(../kozlovskiy-avatar.jpg)", "Козловский", "Играть с ботом", closeModal))
    fetch(`https://${window.location.host}/chess_games?data=${encodeURIComponent(Telegram.WebApp.initData)}`)
        .then(r => r.json())
        .then(r => {
            for (let u of r) {
                let white_turn = u[0][u[0].indexOf(' ') + 1] === 'w'
                // now, it is a white turn, and we're playing for white.
                let statusStr = white_turn && u[1] || !white_turn && !u[1] ?
                    "Ваш ход" : "Ожидание соперника";

                myGames.appendChild(make_game_name(u[4] ? `../p/${u[4]}.jpg` : null, u[3], statusStr, () => {
                    init_mp(u[2])
                    closeModal()
                }))
            }
            document.getElementById("games-loading").remove()
        })
} else init_mp(start_param)
