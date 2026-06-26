const multiplier = document.getElementById("multiplier");
const gameStatus = document.getElementById("gameStatus");
const plane = document.getElementById("plane");

let current = 1.00;
let animation = null;

function startRound() {

    current = 1.00;

    multiplier.innerHTML = current.toFixed(2) + "x";

    gameStatus.innerHTML = "Flying...";

    plane.style.left = "60px";
    plane.style.bottom = "70px";

    // Random crash point (temporary)
    const crashPoint = (Math.random() * 9 + 1).toFixed(2);

    let left = 60;
    let bottom = 70;

    animation = setInterval(() => {

        current += 0.02;

        multiplier.innerHTML = current.toFixed(2) + "x";

        left += 3;
        bottom += 1.8;

        plane.style.left = left + "px";
        plane.style.bottom = bottom + "px";

        if(current >= crashPoint){

            clearInterval(animation);

            multiplier.innerHTML =
            "💥 " + crashPoint + "x";

            gameStatus.innerHTML =
            "CRASHED";

            setTimeout(() => {

                gameStatus.innerHTML =
                "Next round starting...";

                setTimeout(startRound,3000);

            },2000);

        }

    },40);

}

setTimeout(startRound,3000);
