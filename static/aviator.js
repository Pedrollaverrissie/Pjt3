const canvas = document.getElementById("graph");

const ctx = canvas.getContext("2d");

canvas.width = canvas.offsetWidth;
canvas.height = canvas.offsetHeight;

let multiplier = 1;

let x = 40;

let y = canvas.height - 50;

ctx.beginPath();

ctx.moveTo(x,y);

setInterval(()=>{

    multiplier += 0.02;

    document.getElementById("multiplier").innerHTML =
        multiplier.toFixed(2)+"x";

    x += 2;

    y -= multiplier * 0.15;

    ctx.lineWidth = 4;

    ctx.strokeStyle="#00ff88";

    ctx.lineTo(x,y);

    ctx.stroke();

    const rocket = document.querySelector(".rocket");

    rocket.style.left = x+"px";

    rocket.style.top = (y-20)+"px";

},40);
