const gameStatus = document.getElementById("gameStatus");

// Generates a random crash point (temporary)
// Later this will come from Flask
function generateCrashPoint() {

    return Number((Math.random() * 8 + 2).toFixed(2));

}

function startRound() {

    gameStatus.textContent = "Flying...";

    const crashPoint = generateCrashPoint();

    animateFlight(crashPoint);

}

function crashRound(crashPoint) {

    multiplier.textContent = "💥 " + crashPoint.toFixed(2) + "x";

    gameStatus.textContent = "CRASHED";

    addHistory(crashPoint);

    setTimeout(() => {

        gameStatus.textContent = "Next round...";

        setTimeout(startRound, 2000);

    }, 2000);

}
