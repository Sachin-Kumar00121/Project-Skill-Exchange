
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

// 🔹 Back button popup
window.onpageshow = function(event) {
    if (event.persisted) {
        let popup = document.getElementById("bookingPopup");
        if (popup) {
            popup.style.display = "none";
        }
    }
};


// 🔹 24hr to 12hr converter 
function convertTo12Hour(time24) {
    let [hours, minutes] = time24.split(":");
    hours = parseInt(hours);
    let ampm = hours >= 12 ? "PM" : "AM";
    hours = hours % 12;
    hours = hours ? hours : 12;
    return hours + ":" + minutes + " " + ampm;
}

/* DROPDOWN FIX */
const btn = document.querySelector(".register-btn");
const menu = document.querySelector(".dropdown-menu");

btn.addEventListener("click",(e)=>{
e.stopPropagation();
menu.classList.toggle("show");
});

document.addEventListener("click",()=>{
menu.classList.remove("show");
});

/* REPEAT SCROLL ANIMATION */
function revealOnScroll(){
const elements = document.querySelectorAll(".reveal, .fade-left, .zoom-in");

elements.forEach(el=>{
const windowHeight = window.innerHeight;
const top = el.getBoundingClientRect().top;

if(top < windowHeight - 100){
el.classList.add("active");
}else{
el.classList.remove("active"); 
}
});
}

window.addEventListener("scroll", revealOnScroll);
window.addEventListener("load", revealOnScroll);

/* SEARCH SUGGESTION */
const data = ["Car Wash","AC Repair","Computer Repair","Electrician"];

function suggest(){
let input = document.getElementById("searchInput").value.toLowerCase();
let box = document.getElementById("suggestions");

box.innerHTML = "";
if(input==="") return;

data.forEach(item=>{
if(item.toLowerCase().includes(input)){
let div = document.createElement("div");
div.innerText = item;

div.onclick = ()=>{
document.getElementById("searchInput").value = item;
box.innerHTML="";
};

box.appendChild(div);
}
});
}

/* ROUTES */
function goCategory(cat){
window.location.href="/all-skills?category="+cat;
}

function goLogin(){
window.location.href="/login";
}

function goSearch(){
let val=document.getElementById("searchInput").value;
window.location.href="/all-skills?search="+val;
}

