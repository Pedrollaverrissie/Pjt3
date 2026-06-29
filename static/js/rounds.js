const gameStatus = document.getElementById("gameStatus");

async function startRound() {

    // Ask the Flask server for the current game
    const response = await fetch("/game-state");

    const game = await response.json();

    // If waiting
    if (game.status === "waiting") {

        gameStatus.textContent =
            "Next round in " + game.countdown + "s";

        setTimeout(startRound, 1000);

        return;
    }

    // If flying
    if (game.status === "flying") {

        gameStatus.textContent = "Flying...";

        animateFlight(game.current_crash);

        return;
    }

    // If crashed
    if (game.status === "crashed") {

        crashRound(game.current_crash);

        setTimeout(startRound,1000);

    }

}

function crashRound(crashPoint){

    multiplier.textContent =
        "💥 " + crashPoint.toFixed(2) + "x";

    gameStatus.textContent =
        "CRASHED";

    addHistory(crashPoint);

}
