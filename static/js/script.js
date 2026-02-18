
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
