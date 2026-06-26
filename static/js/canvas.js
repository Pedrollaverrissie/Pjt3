// =========================
// Canvas Setup
// =========================

const canvas = document.getElementById("gameCanvas");
const ctx = canvas.getContext("2d");

function resizeCanvas() {

    canvas.width = canvas.offsetWidth;
    canvas.height = canvas.offsetHeight;

}

window.addEventListener("resize", resizeCanvas);
resizeCanvas();


// =========================
// Game Variables
// =========================

let multiplier = 1.00;
let progress = 0;

let crashPoint = randomCrash();

let crashed = false;


// =========================
// Random Crash
// =========================

function randomCrash(){

    return Number((Math.random()*8+2).toFixed(2));

}


// =========================
// Draw Background Grid
// =========================

function drawGrid(){

    ctx.strokeStyle="rgba(255,255,255,.06)";
    ctx.lineWidth=1;

    for(let x=0;x<canvas.width;x+=40){

        ctx.beginPath();
        ctx.moveTo(x,0);
        ctx.lineTo(x,canvas.height);
        ctx.stroke();

    }

    for(let y=0;y<canvas.height;y+=40){

        ctx.beginPath();
        ctx.moveTo(0,y);
        ctx.lineTo(canvas.width,y);
        ctx.stroke();

    }

}
