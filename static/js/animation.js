const plane = document.getElementById("plane");
const path = document.getElementById("flightPath");
const multiplier = document.getElementById("multiplier");

let progress = 0;
let currentMultiplier = 1.00;
let animationInterval = null;

function animateFlight(crashPoint) {

    progress = 0;
    currentMultiplier = 1.00;

    clearInterval(animationInterval);

    animationInterval = setInterval(() => {

        progress += 4;
        currentMultiplier += 0.02;

        multiplier.textContent = currentMultiplier.toFixed(2) + "x";

        // Plane position
        let x = 50 + progress;
        let y = 400 - Math.pow(progress / 18, 1.5);

        plane.style.left = x + "px";
        plane.style.top = y + "px";

        // Draw graph
        path.setAttribute(
            "d",
            `M50 400 Q${50 + progress / 2} ${400 - progress / 4} ${x} ${y}`
        );

        if (currentMultiplier >= crashPoint) {

            clearInterval(animationInterval);

            crashRound(crashPoint);

        }

    }, 40);

}
