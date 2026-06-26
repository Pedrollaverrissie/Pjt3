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
//-------------GRAPH DRWING
function drawGraph(){

    ctx.beginPath();

    ctx.strokeStyle="#00F5A0";

    ctx.shadowBlur=20;
    ctx.shadowColor="#00F5A0";

    ctx.lineWidth=5;

    ctx.moveTo(50,canvas.height-40);

    for(let i=0;i<=progress;i++){

        let x=50+i;

        let y=canvas.height-40-Math.pow(i/18,1.5);

        ctx.lineTo(x,y);

    }

    ctx.stroke();

}
//--------------------DRAW THE PLANE---------------
function drawPlane(){

    let x=50+progress;

    let y=canvas.height-40-Math.pow(progress/18,1.5);

    ctx.font="34px Arial";

    ctx.fillText("✈️",x,y);

}
//---------------DRAW THE MULTIPLIER------------
function drawMultiplier(){

    document.getElementById("multiplier").textContent =
        multiplier.toFixed(2)+"x";

}
//----------------------ANIMATION LOOP--------------
function animate(){

    ctx.clearRect(0,0,canvas.width,canvas.height);

    drawGrid();

    drawGraph();

    drawPlane();

    if(!crashed){

        multiplier+=0.01;

        progress+=2;

        drawMultiplier();

    }

    if(multiplier>=crashPoint){

        crashed=true;

        document.getElementById("multiplier").textContent=
        "💥 "+crashPoint.toFixed(2)+"x";

        document.getElementById("gameStatus").textContent=
        "CRASHED";

        setTimeout(resetRound,3000);

    }

    requestAnimationFrame(animate);

}
//--------------------RESET THE ROUND-------------
function resetRound(){

    multiplier=1.00;

    progress=0;

    crashed=false;

    crashPoint=randomCrash();

    document.getElementById("gameStatus").textContent=
    "Flying...";

}
//---------------------START THE ENGINE------------------
animate();
