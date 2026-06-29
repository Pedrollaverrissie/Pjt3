const gameStatus = document.getElementById("gameStatus");

setInterval(async () => {

    const response = await fetch("/game-state");

    const game = await response.json();

    gameStatus.textContent = game.status;

    if (game.status === "flying") {

        drawFlight(game.multiplier);

    }

    if (game.status === "crashed") {

        drawCrash(game.multiplier);

    }

}, 100);
