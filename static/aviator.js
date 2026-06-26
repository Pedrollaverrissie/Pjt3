let multiplier = 1;

setInterval(function(){

    multiplier += 0.01;

    document.getElementById("multiplier").innerHTML =
        multiplier.toFixed(2) + "x";

},100);
