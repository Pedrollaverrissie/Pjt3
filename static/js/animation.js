const plane = document.getElementById("plane");
const path = document.getElementById("flightPath");
const multiplier = document.getElementById("multiplier");

let lastMultiplier = 1.00;

function drawFlight(mult) {

    multiplier.textContent = mult.toFixed(2) + "x";

    const progress = (mult - 1) * 120;

    const x = 50 + progress;

    const y = 400 - Math.pow(progress / 18, 1.5);

    plane.style.left = x + "px";
    plane.style.top = y + "px";

    path.setAttribute(
        "d",
        `M50 400 Q${50 + progress / 2} ${400 - progress / 4} ${x} ${y}`
    );

    lastMultiplier = mult;

}

function drawCrash(mult) {

    multiplier.textContent = "💥 " + mult.toFixed(2) + "x";

}
