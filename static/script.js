function togglePassword() {
    const password = document.getElementById("password");
    const eyeIcon = document.getElementById("eyeIcon");

    if (password.type === "password") {
        password.type = "text";
        eyeIcon.src = "/static/images/open-eye.jfif";
    } else {
        password.type = "password";
        eyeIcon.src = "/static/images/close-eye.jfif";
    }
}

window.addEventListener("resize", () => {
    const sidebar = document.querySelector(".sidebar");
    const overlay = document.querySelector(".overlay");

    if (window.innerWidth > 768) {
        sidebar.classList.remove("active");
        overlay.classList.remove("active");
    }
});
document.addEventListener("DOMContentLoaded", () => {

    const menuBtn = document.querySelector(".dashboard-menu");
    const cancelBtn = document.querySelector(".cancel");
    const sidebar = document.querySelector(".sidebar");
    const overlay = document.querySelector(".overlay");

    menuBtn.addEventListener("click", () => {
        sidebar.classList.add("active");
        overlay.classList.add("active");
    });

    cancelBtn.addEventListener("click", () => {
        sidebar.classList.remove("active");
        overlay.classList.remove("active");
    });

    overlay.addEventListener("click", () => {
        sidebar.classList.remove("active");
        overlay.classList.remove("active");
    });

});

document.addEventListener("DOMContentLoaded", () => {

    const welcome = document.querySelector(".welcome");

    // show after page loads
    setTimeout(() => {
        welcome.classList.add("show");
    }, 200);

    // hide after 3 seconds (optional)
    setTimeout(() => {
        welcome.classList.remove("show");
    }, 1500);

});

document.addEventListener("DOMContentLoaded", () => {

    const profile = document.getElementById("profileInitial");

    const username = profile.getAttribute("data-username");

    if (username && username.length > 0) {
        profile.textContent = username.charAt(0).toUpperCase();
    } else {
        profile.textContent = "?";
    }

});

const menuBtn = document.getElementById("menuBtn");
const sidebar = document.getElementById("sidebar");

menuBtn.addEventListener("click", () => {
    sidebar.classList.toggle("active");
});


document.addEventListener("DOMContentLoaded", () => {

    const profile = document.getElementById("profile");

    const username = profile.getAttribute("data-username");

    if (username && username.length > 0) {
        profile.textContent = username.charAt(0).toUpperCase();
    } else {
        profile.textContent = "?";
    }

})

/*  OTP TIMER COUNTDOWM*/

document.addEventListener("DOMContentLoaded", function () {

    let timeLeft = 300; // 5 minutes
    const timerDisplay = document.getElementById("timer");

    function updateTimer() {

        let minutes = Math.floor(timeLeft / 60);
        let seconds = timeLeft % 60;

        if (seconds < 10) seconds = "0" + seconds;

        timerDisplay.textContent = minutes + ":" + seconds;

        if (timeLeft <= 0) {
            clearInterval(countdown);
            timerDisplay.textContent = "Expired";
        }

        timeLeft--;
    }

    const countdown = setInterval(updateTimer, 1000);
    updateTimer();
});

