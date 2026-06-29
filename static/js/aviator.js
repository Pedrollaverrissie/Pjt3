let started = false;

async function updateGame() {

    try {

        const response = await fetch("/game-state");
        const game = await response.json();

        // Waiting
        if (game.status === "waiting") {

            started = false;
            resetFlight();
            gameStatus.textContent =
                "Next round in " + game.countdown + "s";

        }


        // Flying
        else if (game.status === "flying") {
        
            started = true;
        
            drawFlight(game.multiplier);
        
            gameStatus.textContent = "✈️ Flying...";
        
        }

        // Crashed
        else if (game.status === "crashed") {
        
            started = false;
        
            drawCrash(game.multiplier);
        
            gameStatus.textContent = "💥 CRASHED";
        
        }

    }

    catch (err) {

        console.log(err);

    }

}

document.addEventListener("DOMContentLoaded", () => {

    console.log("🚀 Supernova Connected");

    setInterval(updateGame, 200);

});                                                                                                         
