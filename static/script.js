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
