document.addEventListener("DOMContentLoaded", function () {

    const toggle = document.getElementById("themeToggle");

    // Load saved theme
    const savedTheme = localStorage.getItem("theme");
    if (savedTheme) {
        document.body.setAttribute("data-theme", savedTheme);
    }

    toggle?.addEventListener("click", function () {

        const current = document.body.getAttribute("data-theme");

        if (current === "dark") {
            document.body.setAttribute("data-theme", "light");
            localStorage.setItem("theme", "light");
        } else {
            document.body.setAttribute("data-theme", "dark");
            localStorage.setItem("theme", "dark");
        }

    });

});

/* Counter Animation */
document.querySelectorAll(".counter").forEach(counter => {
    const updateCount = () => {
        const target = +counter.getAttribute("data-target");
        const count = +counter.innerText;
        const speed = 50;

        const increment = target / speed;

        if (count < target) {
            counter.innerText = Math.ceil(count + increment);
            setTimeout(updateCount, 20);
        } else {
            counter.innerText = target + "+";
        }
    };

    updateCount();
});

//  Number Format (K, L, M)
function formatNumber(num){
if(num >= 1000000){
return (num/1000000).toFixed(1) + "M";
}
else if(num >= 1000){
return (num/1000).toFixed(1) + "K";
}
else{
return num;
}
}

function showToast(message) {
    const toast = document.getElementById("toast");
    toast.innerText = message;
    toast.classList.add("show");

    setTimeout(() => {
        toast.classList.remove("show");
    }, 3000);
}

/* =========================
   CUSTOM CONFIRM FUNCTION
========================= */

function customConfirm(url, message = "Are you sure?") {
    const modal = document.getElementById("confirmModal");
    const text = document.getElementById("confirmText");
    const yesBtn = document.getElementById("confirmYes");
    const noBtn = document.getElementById("confirmNo");

    text.innerText = message;
    modal.style.display = "flex";

    yesBtn.onclick = function () {
        window.location.href = url;
    };

    noBtn.onclick = function () {
        modal.style.display = "none";
    };
}

