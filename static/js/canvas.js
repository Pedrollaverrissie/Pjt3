const canvas = document.getElementById("gameCanvas");
const ctx = canvas.getContext("2d");

function resizeCanvas(){

    canvas.width = canvas.offsetWidth;
    canvas.height = canvas.offsetHeight;

}

window.addEventListener("resize",resizeCanvas);

resizeCanvas();

/*------------------GRID DRAW-------------------*/
function drawGrid(){

    ctx.strokeStyle="rgba(255,255,255,.08)";
    ctx.lineWidth=1;

    for(let x=0;x<canvas.width;x+=40){

        ctx.beginPath();
        ctx.moveTo(x,0);
        ctx.lineTo(x,canvas.height);
        ctx.stroke();

    }

    for(let y=0;y<canvas.height;y+=40){

        ctx.beginPath();
        ctx.moveTo(0,y);
        ctx.lineTo(canvas.width,y);
        ctx.stroke();

    }

}


/*----------------------DRAW THE CURVE-------------------*/
function drawCurve(progress){

    ctx.beginPath();

    ctx.strokeStyle="#00F5A0";

    ctx.lineWidth=5;

    ctx.shadowBlur=20;

    ctx.shadowColor="#00F5A0";

    ctx.moveTo(50,canvas.height-40);

    for(let i=0;i<=progress;i++){

        let x=50+i;

        let y=canvas.height-40-Math.pow(i/18,1.5);

        ctx.lineTo(x,y);

    }

    ctx.stroke();

}
/*-------------------DRAW PLANE-----------------*/

function drawPlane(progress){

    let x=50+progress;

    let y=canvas.height-40-Math.pow(progress/18,1.5);

    ctx.font="34px Arial";

    ctx.fillText("✈️",x,y);

}

/*------------------ANIMATION-----------------------*/

let progress=0;

function animate(){

    ctx.clearRect(0,0,canvas.width,canvas.height);

    drawGrid();

    drawCurve(progress);

    drawPlane(progress);

    progress+=2;

    requestAnimationFrame(animate);

}

animate();





