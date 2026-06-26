function movePlane(x, y) {
    const plane = document.getElementById("plane");
    plane.style.left = x + "px";
    plane.style.top = y + "px";
}

function updateMultiplier(value) {
    document.getElementById("multiplier").textContent =
        value.toFixed(2) + "x";
}

function drawGraph(progress) {

    const path = document.getElementById("flightPath");

    const x = 50 + progress;

    // Curved flight path
    const y = 400 - Math.pow(progress / 18, 1.5);

    path.setAttribute(
        "d",
        `M50 400 Q${50 + progress / 2} ${400 - progress / 4} ${x} ${y}`
    );

    movePlane(x, y);
}
