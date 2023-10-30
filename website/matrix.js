var c = document.getElementById("matrix");
var ctx = c.getContext("2d");

// the characters
var alphabet = "゠アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレワヰヱヲンヺ・ーヽヿ0123456789"
// converting the string into an array of single characters
var characters = alphabet.split("");
var fontSize, columns, drops, lastTime = 0;
init()

function init() {
    fontSize = 12 * devicePixelRatio;

    // making the canvas full screen
    c.height = window.innerHeight * devicePixelRatio;
    c.width = Math.floor(window.innerWidth * devicePixelRatio / fontSize) * fontSize;
    ctx.font = fontSize + "px arial";
    columns = c.width / fontSize;    // number of columns for the rain
    // an array of drops - one per column
    drops = [];

    // x below is the x coordinate
    // 1 = y-coordinate of the drop (same for every drop initially)
    for (var x = 0; x < columns; x++)
        drops[x] = 1;
}

// drawing the characters
function draw(time) {
    // Get the BG color based on the current time i.e. rgb(hh, mm, ss)
    // translucent BG to show trail

    ctx.fillStyle = "rgba(0,0,0, 0.05)";
    ctx.fillRect(0, 0, c.width, c.height);
    ctx.fillStyle = '#0F0';
    var inc = 0.04 * Math.min(16.6, time - lastTime);

    // looping over drops
    for (var i = 0; i < drops.length; i++) {
        // a random chinese character to print
        var text = characters[Math.floor(Math.random() * characters.length)];

        ctx.fillText(text, i * fontSize, drops[i] * fontSize);
        // Incrementing Y coordinate
        drops[i] += inc;
        // sending the drop back to the top randomly after it has crossed the screen
        // adding randomness to the reset to make the drops scattered on the Y axis
        if (drops[i] * fontSize > c.height && Math.random() > 0.975)
            drops[i] = 0;
    }
    lastTime = time
    requestAnimationFrame(draw)
}

window.onresize = init

requestAnimationFrame(draw)