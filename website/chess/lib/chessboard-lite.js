// lite version of chessboard.js v1.0.0
// original library: https://github.com/oakmac/chessboardjs/

// start anonymous scope
;(function () {
    'use strict'

    // ---------------------------------------------------------------------------
    // Constants
    // ---------------------------------------------------------------------------

    let COLUMNS = 'abcdefgh'.split('')
    let REVERSED_COLUMNS = COLUMNS.slice().reverse()
    let START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR'

    // default animation speeds
    let APPEAR_SPEED = 300
    let MOVE_SPEED = 200
    let SNAPBACK_SPEED = 80
    let SNAP_SPEED = 80
    let TRASH_SPEED = 100

    // ---------------------------------------------------------------------------
    // Predicates
    // ---------------------------------------------------------------------------

    function validFen(fen) {
        // cut off any move, castling, etc info from the end
        // we're only interested in position information
        fen = fen.replace(/ .+$/, '')

        // expand the empty square numbers to just 1s
        fen = expandFenEmptySquares(fen)

        // FEN should be 8 sections separated by slashes
        let chunks = fen.split('/')
        if (chunks.length !== 8) return false

        // check each section
        for (let i = 0; i < 8; i++) {
            if (chunks[i].length !== 8 ||
                chunks[i].search(/[^kqrnbpKQRNBP1]/) !== -1) {
                return false
            }
        }

        return true
    }

    // ---------------------------------------------------------------------------
    // Chess Util Functions
    // ---------------------------------------------------------------------------

    // convert FEN piece code to bP, wK, etc
    function fenToPieceCode(piece) {
        // black piece
        if (piece.toLowerCase() === piece) {
            return 'b' + piece.toUpperCase()
        }

        // white piece
        return 'w' + piece.toUpperCase()
    }

    // convert bP, wK, etc code to FEN structure
    function pieceCodeToFen(piece) {
        let pieceCodeLetters = piece.split('')

        // white piece
        if (pieceCodeLetters[0] === 'w') {
            return pieceCodeLetters[1].toUpperCase()
        }

        // black piece
        return pieceCodeLetters[1].toLowerCase()
    }

    // convert FEN string to position object
    // returns false if the FEN string is invalid
    function fenToObj(fen) {
        if (!validFen(fen)) return false

        // cut off any move, castling, etc info from the end
        // we're only interested in position information
        fen = fen.replace(/ .+$/, '')

        let rows = fen.split('/');
        let position = {};

        let currentRow = 8;
        for (let i = 0; i < 8; i++) {
            let row = rows[i].split('');
            let colIdx = 0;

            // loop through each character in the FEN section
            for (let j = 0; j < row.length; j++) {
                // number / empty squares
                if (row[j].search(/[1-8]/) !== -1) {
                    let numEmptySquares = parseInt(row[j], 10);
                    colIdx = colIdx + numEmptySquares
                } else {
                    // piece
                    let square = COLUMNS[colIdx] + currentRow;
                    position[square] = fenToPieceCode(row[j])
                    colIdx = colIdx + 1
                }
            }

            currentRow = currentRow - 1
        }

        return position
    }

    // position object to FEN string
    // returns false if the obj is not a valid position object
    function objToFen(obj) {
        let fen = '';

        let currentRow = 8;
        for (let i = 0; i < 8; i++) {
            for (let j = 0; j < 8; j++) {
                let square = COLUMNS[j] + currentRow

                // piece exists
                if (square in obj) {
                    fen = fen + pieceCodeToFen(obj[square].dataset.piece)
                } else {
                    // empty space
                    fen = fen + '1'
                }
            }

            if (i !== 7) {
                fen = fen + '/'
            }

            currentRow = currentRow - 1
        }

        // squeeze the empty numbers together
        fen = squeezeFenEmptySquares(fen)

        return fen
    }

    function squeezeFenEmptySquares(fen) {
        return fen.replace(/11111111/g, '8')
            .replace(/1111111/g, '7')
            .replace(/111111/g, '6')
            .replace(/11111/g, '5')
            .replace(/1111/g, '4')
            .replace(/111/g, '3')
            .replace(/11/g, '2')
    }

    function expandFenEmptySquares(fen) {
        return fen.replace(/8/g, '11111111')
            .replace(/7/g, '1111111')
            .replace(/6/g, '111111')
            .replace(/5/g, '11111')
            .replace(/4/g, '1111')
            .replace(/3/g, '111')
            .replace(/2/g, '11')
    }

    // returns the distance between two squares
    function squareDistance(squareA, squareB) {
        let squareAArray = squareA.split('')
        let squareAx = COLUMNS.indexOf(squareAArray[0]) + 1
        let squareAy = parseInt(squareAArray[1], 10)

        let squareBArray = squareB.split('')
        let squareBx = COLUMNS.indexOf(squareBArray[0]) + 1
        let squareBy = parseInt(squareBArray[1], 10)

        let xDelta = Math.abs(squareAx - squareBx)
        let yDelta = Math.abs(squareAy - squareBy)

        if (xDelta >= yDelta) return xDelta
        return yDelta
    }

    // returns the square of the closest instance of piece
    // returns false if no instance of piece is found in position
    function findClosestPiece(position, piece, square) {
        // create array of closest squares from square
        let closestSquares = createRadius(square)

        // search through the position in order of distance for the piece
        for (let i = 0; i < closestSquares.length; i++) {
            let s = closestSquares[i]

            if (s in position && position[s] === piece) {
                return s
            }
        }

        return false
    }

    // returns an array of closest squares from square
    function createRadius(square) {
        let i;
        let squares = []

        // calculate distance of all squares
        for (i = 0; i < 8; i++) {
            for (let j = 0; j < 8; j++) {
                let s = COLUMNS[i] + (j + 1);

                // skip the square we're starting from
                if (square === s) continue

                squares.push({
                    square: s,
                    distance: squareDistance(square, s)
                })
            }
        }

        // sort by distance
        squares.sort(function (a, b) {
            return a.distance - b.distance
        })

        // just return the square code
        let surroundingSquares = [];
        for (i = 0; i < squares.length; i++) {
            surroundingSquares.push(squares[i].square)
        }

        return surroundingSquares
    }

    // ---------------------------------------------------------------------------
    // Constructor
    // ---------------------------------------------------------------------------

    function constructor(containerElOrString, config) {
        let container = document.getElementById(containerElOrString)

        // constructor return object
        let widget = {}

        widget.config = config

        // -------------------------------------------------------------------------
        // Stateful
        // -------------------------------------------------------------------------

        let isDragging = false
        let draggedPiece = null
        let draggedPieceSource = null
        let checkSquare = null
        let selectedSquare = null
        let previousSquare = null
        let squareEls = {}
        let squareSize = 16
        let files, ranks;

        let circleEls = []

        // -------------------------------------------------------------------------
        // Markup Building
        // -------------------------------------------------------------------------

        function buildPieceHTML(piece) {
            let p = document.createElement('square')
            p.className = 'piece'
            p.dataset.piece = piece
            return p
        }

        // -------------------------------------------------------------------------
        // Animations
        // -------------------------------------------------------------------------

        function animatePieceToSquare(pieceEl, square, speed, callback) {
            let translateCSS = squareToTranslate(square);

            // animate the piece to the target square
            pieceEl.style.zIndex = '1500';
            pieceEl.animate(
                {transform: translateCSS},
                {duration: speed, easing: "ease"}
            ).onfinish = () => { // when animation finishes
                pieceEl.style.transform = translateCSS
                pieceEl.style.removeProperty('z-index');
                if (typeof callback === 'function') callback()
            }
        }

        function addPiece(square, piece, delay) {
            let newPiece = buildPieceHTML(piece)
            newPiece.style.transform = squareToTranslate(square)
            newPiece.style.opacity = '0';
            squareEls[square] = newPiece;
            container.appendChild(newPiece)

            newPiece.animate(
                {opacity: '1'},
                {duration: APPEAR_SPEED, easing: "ease", delay: delay}
            ).onfinish = () => newPiece.style.removeProperty('opacity');
        }

        function trashPiece(square) {
            let oldPiece = squareEls[square]
            oldPiece.animate(
                {opacity: '0'},
                {duration: TRASH_SPEED, easing: "ease"}
            ).onfinish = () => {
                container.removeChild(oldPiece)
            }
        }

        // do animations that need to happen in order to get
        // from pos1 to pos2
        function animateBoard(pos1, pos2) {
            let i;
            let sq1 = {}
            let sq2 = JSON.parse(JSON.stringify(pos2))

            // remove pieces that are the same in both positions
            for (i in pos1) {
                if (i in pos1 && pos1[i].dataset.piece !== pos2[i]) {
                    sq1[i] = pos1[i].dataset.piece
                }
                if (i in pos2 && pos1[i].dataset.piece === pos2[i]) {
                    delete sq2[i]
                }
            }
            // find all the "move" animations
            for (i in sq2) {
                let closestPiece = findClosestPiece(sq1, sq2[i], i)
                if (closestPiece) {
                    if (i in sq1) { // clear this piece
                        trashPiece(i)
                        delete sq1[i]
                    }

                    let pieceEl = squareEls[closestPiece]
                    squareEls[i] = pieceEl
                    delete squareEls[closestPiece]

                    animatePieceToSquare(pieceEl, i, MOVE_SPEED)

                    delete sq1[closestPiece]
                    delete sq2[i]
                }
            }

            // "add" animations
            let c = 0; // delay counter for pretty animation
            for (i in sq2) {
                addPiece(i, sq2[i], c)
                c += 10;
                delete sq2[i]
            }

            for (i in sq1) { //  "clear" animations
                trashPiece(i)
                delete squareEls[i]
            }
        }

        // -------------------------------------------------------------------------
        // Control Flow
        // -------------------------------------------------------------------------

        function squareToTranslate(square) {
            let i, j;
            if (config.color === 'w') {
                i = COLUMNS.indexOf(square[0])
                j = 8 - square[1]
            } else {
                i = 7 - COLUMNS.indexOf(square[0])
                j = square[1] - 1
            }
            return `translate(calc(${i} * var(--square-size)), calc(${j} * var(--square-size)))`
        }

        function getSquare(x, y) {
            let i = Math.floor((x - container.offsetLeft) / squareSize); // 1 to 8
            let j = Math.floor((container.offsetTop - y) / squareSize) + 9; // a to h
            if (0 <= i && i < 8 && 0 < j && j < 9) {
                if (config.color === 'w')
                    return COLUMNS[i] + j;
                else
                    return COLUMNS[7 - i] + (9 - j);
            } else
                return 'offboard';
        }

        function movePiece(pieceEl, x, y) {
            pieceEl.style.transform = `translate(${x}px, ${y}px)`
        }

        function beginDraggingPiece(x, y) {
            // do nothing if we're not draggable
            if (!config.draggable) return

            if (isDragging) widget.snapbackDraggedPiece()

            cursorMove(x, y)

            let square = getSquare(x, y)

            // move piece by click
            if (!selectedSquare.hidden && draggedPieceSource !== square) {
                if (square in squareEls &&
                    squareEls[square].dataset.piece[0] === config.color) {
                    widget.clearCircles()
                    config.onMouseoverSquare(square)
                } else {
                    isDragging = true
                    stopDraggedPiece(x, y)
                }
            }

            // reset selection if there is no piece on this square
            if (!(square in squareEls)) {
                widget.clearCircles()
                selectedSquare.hidden = true
                return;
            }
            let piece = squareEls[square]

            if (piece.dataset.piece[0] !== config.color) return; // piece is black

            if (piece.getAnimations().length !== 0) return // piece is moving now

            // set state
            isDragging = true
            draggedPiece = piece
            draggedPieceSource = square

            piece.style.zIndex = '1500';

            selectedSquare.hidden = false
            selectedSquare.style.transform = piece.style.transform

            // move the dragged piece
            cursorMove(x, y)
        }

        function cursorMove(x, y) {
            if (isDragging) // put the dragged piece over the mouse cursor
                movePiece(draggedPiece, x - squareSize / 2 - container.offsetLeft, y - squareSize / 2 - container.offsetTop)
            else {
                let square = getSquare(x, y)
                // piece is not selected
                if (previousSquare !== square && selectedSquare.hidden) {
                    widget.clearCircles()
                    if (square in squareEls &&
                        squareEls[square].dataset.piece[0] === config.color)
                        config.onMouseoverSquare(square)
                }
                previousSquare = square
            }
        }

        function stopDraggedPiece(x, y) {
            // do nothing if we are not dragging a piece
            if (!isDragging) return

            // run their onDrop function
            config.onDrop(draggedPieceSource, getSquare(x, y))
            previousSquare = null
        }

        // -------------------------------------------------------------------------
        // Public Methods
        // -------------------------------------------------------------------------

        widget.init = (pos, color) => {
            if (config.color !== undefined && config.color !== color) { // rotate chessboard
                let squareElsReversed = {}
                for (let i in squareEls) {
                    squareElsReversed[COLUMNS[7 - COLUMNS.indexOf(i[0])] + (8 - parseInt(i[1]))] = squareEls[i]
                }
                squareEls = squareElsReversed
            }
            config.color = color

            // init notation
            if (files !== undefined) {
                files.remove()
                ranks.remove()
            }
            files = document.createElement('div')
            files.className = 'files'
            ranks = document.createElement('div')
            ranks.className = 'ranks'
            for (let column of (color === 'w' ? COLUMNS : REVERSED_COLUMNS)) {
                let el = document.createElement('b')
                el.innerText = column
                files.appendChild(el)
            }
            container.appendChild(files)

            for (let i = 8; i > 0; i--) {
                let el = document.createElement('b')
                el.innerText = (color === 'w' ? i : 9 - i).toString()
                ranks.appendChild(el)
            }
            container.appendChild(ranks)

            widget.position(pos)
        }

        // clear the board
        widget.clear = () => {
            widget.position({})
        }

        // shorthand method to get the current FEN
        widget.fen = () => objToFen(squareEls)

        widget.position = position => {
            // start position
            if (position === null)
                position = fenToObj(START_FEN)

            // convert FEN to position object
            else if (validFen(position)) {
                position = fenToObj(position)
            }

            widget.clearCheck()
            animateBoard(squareEls, position)

            if (!selectedSquare.hidden)
                config.onMouseoverSquare(draggedPieceSource)

            else if (!('ontouchstart' in document.documentElement)) // if not touchscreen
                config.onMouseoverSquare(previousSquare)
        }

        widget.resize = () => {
            // calulate the new square size
            squareSize = container.offsetWidth / 8;
            document.documentElement.style.setProperty('--square-size', `${squareSize}px`);
        }

        // set the starting position
        widget.start = () => {
            widget.position(null)
        }

        // set check highlight
        widget.setCheck = square => {
            checkSquare = document.createElement('square')
            checkSquare.className = 'check'
            checkSquare.style.transform = squareToTranslate(square)
            container.appendChild(checkSquare)
        }
        widget.clearCheck = () => {
            if (checkSquare !== null)
                container.removeChild(checkSquare)
            checkSquare = null
        }

        widget.addCircle = square => {
            let newCircle = document.createElement('square')
            newCircle.className = square in squareEls ? 'dest eat' : 'dest';
            newCircle.style.transform = squareToTranslate(square)
            container.appendChild(newCircle)

            circleEls.push(newCircle)
        }
        widget.clearCircles = () => {
            while (circleEls.length !== 0)
                container.removeChild(circleEls.pop())
        }

        widget.snapbackDraggedPiece = () => {
            // set state
            isDragging = false

            animatePieceToSquare(draggedPiece, draggedPieceSource, SNAPBACK_SPEED)
        }

        widget.dropDraggedPieceOnSquare = (square, fen) => {
            // set state
            isDragging = false

            selectedSquare.hidden = true
            previousSquare = square
            widget.clearCircles()

            if (square in squareEls) // clear this piece
                trashPiece(square)

            squareEls[square] = squareEls[draggedPieceSource]
            delete squareEls[draggedPieceSource]

            animatePieceToSquare(draggedPiece, square, SNAP_SPEED, config.onSnapEnd)
            widget.position(fen)
        };


        // -------------------------------------------------------------------------
        // Initialization
        // -------------------------------------------------------------------------

        function addEvents() {
            document.addEventListener("touchstart", function () {
            }, true);

            window.onpointerdown = e => beginDraggingPiece(e.pageX, e.pageY)
            window.onpointermove = e => cursorMove(e.pageX, e.pageY)
            window.onpointercancel = window.onpointerup = e => stopDraggedPiece(e.pageX, e.pageY)

            // resize chessboard
            window.onresize = widget.resize

            container.oncontextmenu = e => e.preventDefault()
        }

        function initDOM() {
            selectedSquare = document.createElement('square')
            selectedSquare.className = 'selected'
            selectedSquare.hidden = true
            container.appendChild(selectedSquare)

            // set the size and draw the board
            widget.resize()
        }

        // -------------------------------------------------------------------------
        // Initialization
        // -------------------------------------------------------------------------

        initDOM()
        addEvents()

        // return the widget object
        return widget
    } // end constructor

    window['Chessboard'] = constructor
})() // end anonymous wrapper
