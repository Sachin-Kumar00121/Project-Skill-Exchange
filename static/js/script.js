
function togglePassword(id) {
    var input = document.getElementById(id);

    if (input.type === "password") {
        input.type = "text";
    } else {
        input.type = "password";
    }
}

function checkStrength() {
    var password = document.getElementById("password").value;
    var message = document.getElementById("strengthMessage");

    var strength = 0;

    if (password.length >= 8) strength++;
    if (password.match(/[a-z]/)) strength++;
    if (password.match(/[A-Z]/)) strength++;
    if (password.match(/[0-9]/)) strength++;
    if (password.match(/[@$!%*?&]/)) strength++;

    if (strength <= 2) {
        message.innerHTML = "Weak Password";
        message.style.color = "red";
    } 
    else if (strength == 3 || strength == 4) {
        message.innerHTML = "Medium Strength";
        message.style.color = "orange";
    } 
    else {
        message.innerHTML = "Strong Password";
        message.style.color = "green";
    }
}

function openPopup(skillId, price, unit) {
    document.getElementById("bookingPopup").style.display = "block";
    document.getElementById("popupSkillId").value = skillId;
    document.getElementById("popupPrice").value = price;
    document.getElementById("popupUnit").value = unit;
}

function closePopup() {
    document.getElementById("bookingPopup").style.display = "none";
}

// 🔹 Back button popup fix
window.onpageshow = function(event) {
    if (event.persisted) {
        let popup = document.getElementById("bookingPopup");
        if (popup) {
            popup.style.display = "none";
        }
    }
};


// 🔹 24hr to 12hr converter (अगर future में जरूरत हो)
function convertTo12Hour(time24) {
    let [hours, minutes] = time24.split(":");
    hours = parseInt(hours);
    let ampm = hours >= 12 ? "PM" : "AM";
    hours = hours % 12;
    hours = hours ? hours : 12;
    return hours + ":" + minutes + " " + ampm;
}
