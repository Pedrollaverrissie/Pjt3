function togglePassword() {

    const password =
        document.getElementById("password");

    const eyeIcon =
        document.getElementById("eyeIcon");

    if (!password || !eyeIcon) {
        return;
    }

    if (password.type === "password") {

        password.type = "text";

        eyeIcon.src =
            "/static/images/open-eye.jfif";

    } else {

        password.type = "password";

        eyeIcon.src =
            "/static/images/close-eye.jfif";
    }
}


/* =====================================================
   SIDEBAR
===================================================== */

window.addEventListener("resize", () => {

    const sidebar =
        document.querySelector(".sidebar");

    const overlay =
        document.querySelector(".overlay");

    if (!sidebar || !overlay) {
        return;
    }

    if (window.innerWidth > 768) {

        sidebar.classList.remove("active");

        overlay.classList.remove("active");
    }

});


document.addEventListener("DOMContentLoaded", () => {

    const menuBtn =
        document.querySelector(".dashboard-menu");

    const cancelBtn =
        document.querySelector(".cancel");

    const sidebar =
        document.querySelector(".sidebar");

    const overlay =
        document.querySelector(".overlay");


    if (!menuBtn || !cancelBtn || !sidebar || !overlay) {
        return;
    }


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


/* =====================================================
   WELCOME MESSAGE
===================================================== */

document.addEventListener("DOMContentLoaded", () => {

    const welcome =
        document.querySelector(".welcome");

    if (!welcome) {
        return;
    }

    setTimeout(() => {

        welcome.classList.add("show");

    }, 200);


    setTimeout(() => {

        welcome.classList.remove("show");

    }, 1500);

});


/* =====================================================
   PROFILE INITIAL
===================================================== */

document.addEventListener("DOMContentLoaded", () => {

    const profile =
        document.getElementById("profile");

    if (!profile) {
        return;
    }

    const username =
        profile.getAttribute("data-username");

    if (username && username.length > 0) {

        profile.textContent =
            username.charAt(0).toUpperCase();

    } else {

        profile.textContent = "?";

    }

});


/* =====================================================
   OTP TIMER COUNTDOWN
===================================================== */

document.addEventListener("DOMContentLoaded", function () {

    const timerDisplay =
        document.getElementById("timer");

    /*
       Dashboard does not have an OTP timer.
       Therefore do nothing on dashboard.
    */

    if (!timerDisplay) {
        return;
    }


    let timeLeft = 300;


    function updateTimer() {

        let minutes =
            Math.floor(timeLeft / 60);

        let seconds =
            timeLeft % 60;


        if (seconds < 10) {
            seconds =
                "0" + seconds;
        }


        timerDisplay.textContent =
            minutes + ":" + seconds;


        if (timeLeft <= 0) {

            clearInterval(countdown);

            timerDisplay.textContent =
                "Expired";

            return;
        }


        timeLeft--;

    }


    const countdown =
        setInterval(
            updateTimer,
            1000
        );


    updateTimer();

});


/* =====================================================
   COPY REFERRAL LINK
===================================================== */

function copyReferralLink() {

    const linkInput =
        document.getElementById("referralLink");

    const btn =
        document.getElementById("copyBtn");


    if (!linkInput || !btn) {
        return;
    }


    const link =
        linkInput.value;


    navigator.clipboard.writeText(link);


    btn.innerHTML =
        "✅ Copied!";


    setTimeout(() => {

        btn.innerHTML =
            "📋 COPY LINK";

    }, 2000);

}