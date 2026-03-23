const authWrapper = document.querySelector('.auth-wrapper');
const loginTrigger = document.querySelector('.login-trigger');
const registerTrigger = document.querySelector('.register-trigger');

// Toggle login & sign up page
if(registerTrigger){
    registerTrigger.addEventListener('click', (e) => {
        e.preventDefault();
        authWrapper.classList.add('toggled');
       
        document.querySelectorAll('.error-msg').forEach(msg => msg.style.display = 'none');
    });
}

if(loginTrigger){
    loginTrigger.addEventListener('click', (e) => {
        e.preventDefault();
        authWrapper.classList.remove('toggled');
        
        document.querySelectorAll('.error-msg').forEach(msg => msg.style.display = 'none');
    });
}

// ROLE SELECT
function setRole(role, el){
    document.getElementById("roleInput").value = role;

    document.querySelectorAll(".role-buttons button").forEach(btn=>{
        btn.classList.remove("active");
    });

    el.classList.add("active");
}

window.onload = function(){
    if(window.location.hash === "#signup"){
        document.querySelector('.auth-wrapper').classList.add('toggled');
    }
}

// PASSWORD STRENGTH
function checkStrength() {
    let password = document.getElementById("pass").value;
    let message = document.getElementById("strengthMessage");

    let strength = 0;

    if (password.length >= 8) strength++;
    if (password.match(/[a-z]/)) strength++;
    if (password.match(/[A-Z]/)) strength++;
    if (password.match(/[0-9]/)) strength++;
    if (password.match(/[@$!%*?&]/)) strength++;

    if (strength <= 2) {
        message.innerHTML = "Weak Password";
        message.style.color = "red";
    } 
    else if (strength <= 4) {
        message.innerHTML = "Medium Strength";
        message.style.color = "orange";
    } 
    else {
        message.innerHTML = "Strong Password";
        message.style.color = "green";
    }
}

// FORM VALIDATION
let form = document.getElementById("signupForm");

if(form){
    form.addEventListener("submit", function(e){
        let role = document.getElementById("roleInput").value;
        if(!role){
            e.preventDefault();
           
            document.getElementById('customAlert').classList.add('show');
        }
    });
}

function closeAlert() {
    document.getElementById('customAlert').classList.remove('show');
}

// togle password

function togglePassword(id, el){
    let input = document.getElementById(id);

    if(input.type === "password"){
        input.type = "text";

        // lock → unlock
        el.classList.remove("fa-lock");
        el.classList.add("fa-lock-open");
    } else {
        input.type = "password";

        // unlock → lock
        el.classList.remove("fa-lock-open");
        el.classList.add("fa-lock");
    }
}

