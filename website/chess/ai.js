importScripts('lib/chess.js')

var game = new Chess();

var undo_stack = [];
var STACK_SIZE = 50; // maximum size of undo stack

var FLAG_EXACT = 0;
var FLAG_UPPER = 1;
var FLAG_LOWER = 2;

/* Zobrist hashing algorithm */


/**
 * Returns function which accepts a board object as its only parameter and returns a unique hash value based on that
 * board's position.
 *
 * This function is curried so it only needs to be called once. The returned hash function can be called many times.
 */
function setupZobristHashing() {
    var N_BITS = 32;

    var pieceValues = {
        'w': {
            'p': 1,  // White pawn
            'r': 2,  // White rook
            'n': 3,  // White knight
            'b': 4,  // White bishop
            'q': 5,  // White queen
            'k': 6   // White king
        },

        'b': {
            'p': 7,  // Black pawn
            'r': 8,  // Black rook
            'n': 9,  // Black knight
            'b': 10, // Black bishop
            'q': 11, // Black queen
            'k': 12  // Black king
        }
    };

    var zobristLookupTable = [];

    // For each of the 64 squares on the board
    for (var i = 0; i < 64; ++i) {
        zobristLookupTable.push(new Uint32Array(12));

        // For each of the 12 possible piece types (i.e. entries in `pieceValues` maps 6 piece types for each player color)
        for (var j = 0; j < 12; ++j) {
            var randomBitstring = Math.random() * Math.pow(2, N_BITS);  // Subtract 2 from N_BITS to prevent overflow

            // Each square, piece state maps to a random bitstring which will be used to generate a unique hash value
            zobristLookupTable[i][j] = randomBitstring;
        }
    }

    /**
     * A fast hash function which maps a board state to a unique integer
     */
    return function (board) {
        var h = 0;

        /*
         TODO: It'd be nice if we could iterate over pieces on the board here instead of each of the 64 squares as there
         can only be a maximum of 12 pieces on the board at any given time. I don't think this is easily supported by
         chess.js, however.
         */
        for (var i = 0; i < board.length; ++i) {
            for (var j = 0; j < board.length; ++j) {
                var square = board[i][j];

                if (square) {
                    h ^= (pieceValues[square.color][square.type] * zobristLookupTable[i][j])
                }
            }
        }

        return h
    };
}

var getZobristHash = setupZobristHashing();

/* Transposition table */

/**
 * The transposition table is a large cache of moves we've previously explored with minimax.
 *
 * Storing prior moves allows us to speed up future moves by retrieving the game state of previously explored moves in
 * our decision tree.
 */

// We need to set a limit on the number of moves
var TABLE_SIZE = 2e6;

transpositionTable = new Array(TABLE_SIZE);

/**
 * The transposition table is implemented by a fixed-size array.
 *
 * We can then map a Zobrist hash value of a game state to an index in our array by using a modulus.
 */
var transpositionTableIdx = function (zobristKey) {
    return Math.abs(zobristKey) % TABLE_SIZE;
};

/**
 * Insert a move into the transposition table
 *
 * @param zobristKey A zobrist hash of this move's position
 * @param depth The minimax depth this move was calculated at
 * @param value The best evaluation score for this move's position
 * @param flag Whether or not we exceeded alpha or beta. There are three possibilities:
 *    - alpha/beta were not exceeded (FLAG_EXACT)
 *    - we exceeded alpha (FLAG_UPPER)
 *    - we fell below beta (FLAG_LOWER)
 */
var transpositionTablePut = function (zobristKey, depth, value, move, flag) {
    var idx = transpositionTableIdx(zobristKey);

    var previousValue = transpositionTable[idx];
    var newValue;

    if (previousValue && (previousValue.hash == zobristKey)) {
        if (previousValue.depth > depth) {
            newValue = previousValue;
        }
    } else {
        newValue = {
            hash: zobristKey,
            depth: depth,
            value: value,
            move: move,
            flag: flag
        }
    }

    transpositionTable[idx] = newValue;
};

/**
 * Fetch a move from the transposition table via a given zobristKey, returns null if no move was found.
 */
var transpositionTableGet = function (zobristKey) {
    var idx = transpositionTableIdx(zobristKey);

    var previousValue = transpositionTable[idx];

    // We need to check the hash matches, since it's possible two different board states can map to the same
    // transposition table index
    if (previousValue && (previousValue.hash == zobristKey)) {
        return previousValue
    } else {
        return null
    }
};

var swapMoves = function (arr, sourceIdx, destIdx) {
    var temp = arr[sourceIdx];

    arr[sourceIdx] = arr[destIdx];
    arr[destIdx] = temp;

    return arr;
};

var uglyMoveKey = function (ugly_move) {
    return ugly_move.color + ugly_move.piece + ugly_move.from + ugly_move.to
};

/*The "AI" part starts here */

var minimaxRoot = function (depth, game, isMaximisingPlayer) {

    var newGameMoves = game.ugly_moves();
    var bestMove = -9999;
    var bestMoveFound;

    for (var i = 0; i < newGameMoves.length; i++) {
        var newGameMove = newGameMoves[i]
        game.simple_move(newGameMove);
        var value = minimax(depth - 1, game, -10000, 10000, !isMaximisingPlayer);
        game.simple_undo();
        if (value >= bestMove) {
            bestMove = value;
            bestMoveFound = newGameMove;
        }
    }
    return bestMoveFound;
};

var minimax = function (depth, game, alpha, beta, isMaximisingPlayer) {

    if (depth === 0) {
        return -evaluateBoard(game.board());
    }

    var zobristKey = getZobristHash(game.board());
    var cachedBoardState = transpositionTableGet(zobristKey);

    if (cachedBoardState && cachedBoardState.depth > depth) {
        if (cachedBoardState.flag == FLAG_EXACT)
            return cachedBoardState.value;

        if (cachedBoardState.flag == FLAG_UPPER)
            beta = Math.min(beta, cachedBoardState.value);

        if (cachedBoardState.flag == FLAG_LOWER)
            alpha = Math.max(alpha, cachedBoardState.value);

        if (alpha > beta)
            return cachedBoardState.value;
    }

    var newGameMoves = game.ugly_moves();
    var bestMove;
    var bestMoveFound;

    if (isMaximisingPlayer) {
        bestMove = -9999;

        if (cachedBoardState && cachedBoardState.depth <= depth &&
            (cachedBoardState.flag == FLAG_UPPER || cachedBoardState.flag == FLAG_EXACT)
        ) {
            for (var i = 0; i < newGameMoves.length; i++) {
                if (uglyMoveKey(newGameMoves[i]) == uglyMoveKey(cachedBoardState.move)) {
                    swapMoves(newGameMoves, 0, i);

                    break;
                }
            }
        }

        for (var i = 0; i < newGameMoves.length; i++) {
            game.simple_move(newGameMoves[i]);
            var nextMoveValue = minimax(depth - 1, game, alpha, beta, !isMaximisingPlayer);
            game.simple_undo();

            if (nextMoveValue > bestMove) {
                bestMove = nextMoveValue;
                bestMoveFound = newGameMoves[i];
            }

            alpha = Math.max(alpha, bestMove);

            if (beta <= alpha) {
                transpositionTablePut(zobristKey, depth, bestMove, bestMoveFound, FLAG_UPPER);
                return bestMove;
            }
        }
    } else {
        bestMove = 9999;

        if (cachedBoardState && cachedBoardState.depth <= depth &&
            (cachedBoardState.flag == FLAG_LOWER || cachedBoardState.flag == FLAG_EXACT)
        ) {
            for (var i = 0; i < newGameMoves.length; i++) {
                if (uglyMoveKey(newGameMoves[i]) == uglyMoveKey(cachedBoardState.move)) {
                    swapMoves(newGameMoves, 0, i);

                    break;
                }
            }
        }

        for (var i = 0; i < newGameMoves.length; i++) {
            game.simple_move(newGameMoves[i]);
            var nextMoveValue = minimax(depth - 1, game, alpha, beta, !isMaximisingPlayer);
            game.simple_undo();

            if (nextMoveValue < bestMove) {
                bestMove = nextMoveValue;
                bestMoveFound = newGameMoves[i];
            }

            beta = Math.min(beta, bestMove);

            if (beta <= alpha) {
                transpositionTablePut(zobristKey, depth, bestMove, bestMoveFound, FLAG_LOWER);
                return bestMove;
            }
        }
    }

    transpositionTablePut(zobristKey, depth, bestMove, bestMoveFound, FLAG_EXACT);
    return bestMove;
};

var evaluateBoard = function (board) {
    var totalEvaluation = 0;
    for (var i = 0; i < 8; i++) {
        for (var j = 0; j < 8; j++) {
            totalEvaluation = totalEvaluation + getPieceValue(board[i][j], i, j);
        }
    }
    return totalEvaluation;
};

var reverseArray = function (array) {
    return array.slice().reverse();
};

var pawnEvalWhite =
    [
        [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        [5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0],
        [1.0, 1.0, 2.0, 3.0, 3.0, 2.0, 1.0, 1.0],
        [0.5, 0.5, 1.0, 2.5, 2.5, 1.0, 0.5, 0.5],
        [0.0, 0.0, 0.0, 2.0, 2.0, 0.0, 0.0, 0.0],
        [0.5, -0.5, -1.0, 0.0, 0.0, -1.0, -0.5, 0.5],
        [0.5, 1.0, 1.0, -2.0, -2.0, 1.0, 1.0, 0.5],
        [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    ];

var pawnEvalBlack = reverseArray(pawnEvalWhite);

var knightEval =
    [
        [-5.0, -4.0, -3.0, -3.0, -3.0, -3.0, -4.0, -5.0],
        [-4.0, -2.0, 0.0, 0.0, 0.0, 0.0, -2.0, -4.0],
        [-3.0, 0.0, 1.0, 1.5, 1.5, 1.0, 0.0, -3.0],
        [-3.0, 0.5, 1.5, 2.0, 2.0, 1.5, 0.5, -3.0],
        [-3.0, 0.0, 1.5, 2.0, 2.0, 1.5, 0.0, -3.0],
        [-3.0, 0.5, 1.0, 1.5, 1.5, 1.0, 0.5, -3.0],
        [-4.0, -2.0, 0.0, 0.5, 0.5, 0.0, -2.0, -4.0],
        [-5.0, -4.0, -3.0, -3.0, -3.0, -3.0, -4.0, -5.0]
    ];

var bishopEvalWhite = [
    [-2.0, -1.0, -1.0, -1.0, -1.0, -1.0, -1.0, -2.0],
    [-1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, -1.0],
    [-1.0, 0.0, 0.5, 1.0, 1.0, 0.5, 0.0, -1.0],
    [-1.0, 0.5, 0.5, 1.0, 1.0, 0.5, 0.5, -1.0],
    [-1.0, 0.0, 1.0, 1.0, 1.0, 1.0, 0.0, -1.0],
    [-1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, -1.0],
    [-1.0, 0.5, 0.0, 0.0, 0.0, 0.0, 0.5, -1.0],
    [-2.0, -1.0, -1.0, -1.0, -1.0, -1.0, -1.0, -2.0]
];

var bishopEvalBlack = reverseArray(bishopEvalWhite);

var rookEvalWhite = [
    [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    [0.5, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.5],
    [-0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, -0.5],
    [-0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, -0.5],
    [-0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, -0.5],
    [-0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, -0.5],
    [-0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, -0.5],
    [0.0, 0.0, 0.0, 0.5, 0.5, 0.0, 0.0, 0.0]
];

var rookEvalBlack = reverseArray(rookEvalWhite);

var evalQueen = [
    [-2.0, -1.0, -1.0, -0.5, -0.5, -1.0, -1.0, -2.0],
    [-1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, -1.0],
    [-1.0, 0.0, 0.5, 0.5, 0.5, 0.5, 0.0, -1.0],
    [-0.5, 0.0, 0.5, 0.5, 0.5, 0.5, 0.0, -0.5],
    [0.0, 0.0, 0.5, 0.5, 0.5, 0.5, 0.0, -0.5],
    [-1.0, 0.5, 0.5, 0.5, 0.5, 0.5, 0.0, -1.0],
    [-1.0, 0.0, 0.5, 0.0, 0.0, 0.0, 0.0, -1.0],
    [-2.0, -1.0, -1.0, -0.5, -0.5, -1.0, -1.0, -2.0]
];

var kingEvalWhite = [

    [-3.0, -4.0, -4.0, -5.0, -5.0, -4.0, -4.0, -3.0],
    [-3.0, -4.0, -4.0, -5.0, -5.0, -4.0, -4.0, -3.0],
    [-3.0, -4.0, -4.0, -5.0, -5.0, -4.0, -4.0, -3.0],
    [-3.0, -4.0, -4.0, -5.0, -5.0, -4.0, -4.0, -3.0],
    [-2.0, -3.0, -3.0, -4.0, -4.0, -3.0, -3.0, -2.0],
    [-1.0, -2.0, -2.0, -2.0, -2.0, -2.0, -2.0, -1.0],
    [2.0, 2.0, 0.0, 0.0, 0.0, 0.0, 2.0, 2.0],
    [2.0, 3.0, 1.0, 0.0, 0.0, 1.0, 3.0, 2.0]
];

var kingEvalBlack = reverseArray(kingEvalWhite);


var getPieceValue = function (piece, x, y) {
    if (piece === null) {
        return 0;
    }
    var getAbsoluteValue = function (piece, isWhite, x, y) {
        if (piece.type === 'p') {
            return 10 + (isWhite ? pawnEvalWhite[y][x] : pawnEvalBlack[y][x]);
        } else if (piece.type === 'r') {
            return 50 + (isWhite ? rookEvalWhite[y][x] : rookEvalBlack[y][x]);
        } else if (piece.type === 'n') {
            return 30 + knightEval[y][x];
        } else if (piece.type === 'b') {
            return 30 + (isWhite ? bishopEvalWhite[y][x] : bishopEvalBlack[y][x]);
        } else if (piece.type === 'q') {
            return 90 + evalQueen[y][x];
        } else if (piece.type === 'k') {
            return 900 + (isWhite ? kingEvalWhite[y][x] : kingEvalBlack[y][x]);
        }
        throw "Unknown piece type: " + piece.type;
    };

    var absoluteValue = getAbsoluteValue(piece, piece.color === 'w', x, y);
    return piece.color === 'w' ? absoluteValue : -absoluteValue;
};

function undo() {
    undo_stack.push(game.undo());

    // Maintain a maximum stack size
    if (undo_stack.length > STACK_SIZE)
        undo_stack.shift();
}

function redo() {
    game.move(undo_stack.pop());
}

onmessage = e => {
    let d = e.data;
    switch (d.cmd) {
        case 'ai':
            game.ugly_move(minimaxRoot(d.depth, game, true));
            break
        case 'snapEnd':
            postMessage({
                cmd: d.cmd,
                fen: game.fen(),
                history: game.history()
            })
            break
        case 'move':
            let move = game.move({
                from: d.source,
                to: d.target,
                promotion: 'q'
            });
            if (move === null)
                postMessage({
                    cmd: d.cmd,
                    action: 'snapback'
                })
            else
                postMessage({
                    cmd: d.cmd,
                    action: 'drop',
                    target: d.target,
                    history: game.history(),
                    fen: game.fen()
                })
            break
        case 'status':
            let title = 'Ничья';
            let description;
            let status;
            let type = 'end';
            let is_check;
            if (game.in_checkmate()) {
                is_check = true
                if (game.turn() === 'w') {
                    title = 'Мат белым'
                    description = 'Вы проиграли'
                } else {
                    title = 'Мат чёрным'
                    description = 'Вы выиграли'
                }
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
            postMessage({
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
            postMessage({
                cmd: d.cmd,
                moves: moves,
                square: d.square
            })
            break
        case 'undo':
            let hist_len = game.history().length;
            if (hist_len <= 2)
                postMessage({
                    cmd: d.cmd,
                    do: false
                })
            if (hist_len >= 2) {
                // Undo twice: Opponent's latest move, followed by player's latest move
                undo()
                undo()
                postMessage({
                    cmd: d.cmd,
                    do: true,
                    fen: game.fen(),
                    history: game.history()
                })
            }
            break
        case 'redo':
            if (undo_stack.length <= 2) {
                postMessage({
                    cmd: d.cmd,
                    do: false
                })
            }
            if (undo_stack.length >= 2) {
                // Redo twice: Player's last move, followed by opponent's last move
                redo()
                redo()
                postMessage({
                    cmd: d.cmd,
                    do: true,
                    fen: game.fen(),
                    history: game.history()
                })
            }
            break
        case 'pos':
            if (d.fen) game.load(d.fen)
            else game.reset()

            undo_stack = []

            postMessage({
                cmd: d.cmd,
                white: game.turn() === 'w'
            })
            break
        case 'restart': // stub
            postMessage({cmd: d.cmd})
            break
    }
}