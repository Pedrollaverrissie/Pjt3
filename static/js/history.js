function addHistory(crashMultiplier) {

    const history = document.querySelector(".history");

    const item = document.createElement("span");

    item.textContent = crashMultiplier.toFixed(2) + "x";

    // Red if crash below 2x
    if (crashMultiplier < 2) {
        item.classList.add("red");
    } else {
        item.classList.add("green");
    }

    // Add newest result first
    history.prepend(item);

    // Keep only the latest 10 results
    while (history.children.length > 10) {
        history.removeChild(history.lastChild);
    }

}
