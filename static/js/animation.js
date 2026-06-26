
function movePlane(x, y) {
    const plane = document.getElementById("plane");

    plane.style.left = x + "px";
    plane.style.top = y + "px";
}

function updateMultiplier(value) {
    document.getElementById("multiplier").innerHTML =
        value.toFixed(2) + "x";
}
