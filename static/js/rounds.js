function startRound() {

    let current = 1;
    let progress = 0;

    const crashPoint = Number((Math.random() * 8 + 2).toFixed(2));

    document.getElementById("gameStatus").textContent = "Flying...";

    const timer = setInterval(() => {

        current += 0.02;
        progress += 4;

        updateMultiplier(current);
        drawGraph(progress);

        if (current >= crashPoint) {

            clearInterval(timer);

            document.getElementById("multiplier").textContent =
                "💥 " + crashPoint.toFixed(2) + "x";

            document.getElementById("gameStatus").textContent =
                "CRASHED";

            addHistory(crashPoint);

            setTimeout(startRound, 3000);
        }

    }, 40);
}
