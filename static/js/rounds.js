function startRound() {

    let current = 1.00;
    let left = 60;
    let top = 350;

    const gameStatus = document.getElementById("gameStatus");
    const multiplier = document.getElementById("multiplier");

    gameStatus.innerHTML = "Flying...";

    const crashPoint = Number((Math.random() * 8 + 2).toFixed(2));

    const timer = setInterval(() => {

        current += 0.02;

        // Update multiplier
        updateMultiplier(current);

        // Move plane
        left += 3;
        top -= 1.4;

        movePlane(left, top);

        // Crash
        if (current >= crashPoint) {

            clearInterval(timer);

            multiplier.innerHTML = "💥 " + crashPoint.toFixed(2) + "x";

            gameStatus.innerHTML = "CRASHED";

            addHistory(crashPoint);

            setTimeout(() => {

                gameStatus.innerHTML = "Next Round...";

                setTimeout(startRound, 3000);

            }, 2000);
        }

    }, 40);
}

function crashRound() {
    console.log("Round Crashed");
}
