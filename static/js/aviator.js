document.addEventListener("DOMContentLoaded", () => {

    const multiplier = document.getElementById("multiplier");
    const gameStatus = document.getElementById("gameStatus");
    const plane = document.getElementById("plane");
    const path = document.getElementById("flightPath");

    function startRound(){

        let current = 1;
        let progress = 0;

        const crashPoint = Number((Math.random()*8+2).toFixed(2));

        multiplier.innerHTML="1.00x";
        gameStatus.innerHTML="Flying...";

        const timer = setInterval(()=>{

            current +=0.02;

            multiplier.innerHTML=current.toFixed(2)+"x";

            progress +=4;

            const x = 50 + progress;

            const y = 400 - Math.pow(progress/22,1.5);

            plane.style.left=x+"px";
            plane.style.top=y+"px";

            path.setAttribute(
                "d",
                `M50 400 Q${x/2} ${400-(progress/5)} ${x} ${y}`
            );

            if(current>=crashPoint){

                clearInterval(timer);

                multiplier.innerHTML="💥 "+crashPoint.toFixed(2)+"x";

                gameStatus.innerHTML="CRASHED";

                setTimeout(startRound,3000);

            }

        },40);

    }

    setTimeout(startRound,2000);

});
