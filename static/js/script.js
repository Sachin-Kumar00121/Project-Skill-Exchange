 // book popup 

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

/* Counter Animation */
let counterStarted = false;

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

function startCounters(){
if(counterStarted) return;

const counters = document.querySelectorAll(".counter");

counters.forEach(counter => {

const target = +counter.getAttribute("data-target");
let count = 0;
const speed = 60;
const increment = target / speed;

function updateCount(){
if(count < target){
count += increment;
counter.innerText = formatNumber(Math.ceil(count));
setTimeout(updateCount, 25);
} else {
counter.innerText = formatNumber(target) + "+";
}
}

updateCount();
});

counterStarted = true;
}

//  Scroll trigger
window.addEventListener("scroll", () => {
const section = document.querySelector(".section");

if(section){
const top = section.getBoundingClientRect().top;
const windowHeight = window.innerHeight;

if(top < windowHeight - 30){
startCounters();
}
}
});

// ACTIVE LINK
document.querySelectorAll(".nav-links a").forEach(link=>{
if(link.href === window.location.href){
link.classList.add("active");
}
});

//  SCROLL ANIMATION 
function revealOnScroll(){
const elements = document.querySelectorAll(".reveal, .fade-left, .zoom-in");

elements.forEach((el,i)=>{
const top = el.getBoundingClientRect().top;
const windowHeight = window.innerHeight;

if(top < windowHeight - 30){
setTimeout(()=>{
el.classList.add("active");
}, i * 80);
}else{
el.classList.remove("active"); 
}
});
}

window.addEventListener("scroll", revealOnScroll);
window.addEventListener("load", revealOnScroll);

// SMOOTH SCROLL
document.querySelectorAll('a[href^="#"]').forEach(anchor=>{
anchor.addEventListener("click",function(e){
e.preventDefault();
document.querySelector(this.getAttribute("href"))
.scrollIntoView({behavior:"smooth"});
});
});

// ROUTES
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

// LIVE SEARCH
let timer;

function suggestLive(){
clearTimeout(timer);

timer = setTimeout(()=>{

let input = document.getElementById("searchInput").value;
let box = document.getElementById("suggestions");

if(input.length < 1){
box.innerHTML = "";
return;
}

fetch("/search-suggest?q="+input)
.then(res => res.json())
.then(data=>{
box.innerHTML = "";

data.forEach(item=>{
let div = document.createElement("div");
div.innerText = item;

div.onclick = ()=>{
document.getElementById("searchInput").value = item;
box.innerHTML="";
};

box.appendChild(div);
});
});

},300);
}

/* PASSWORD TOGGLE */
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

/* PASSWORD STRENGTH */
function checkStrength() {
    var password = document.getElementById("new_password").value;
    var strength = document.getElementById("strength");

    if (password.length < 8) {
        strength.innerHTML = "Weak (minimum 8 characters)";
        strength.style.color = "red";
        return;
    }

    var strongRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])/;

    if (strongRegex.test(password)) {
        strength.innerHTML = "Strong Password";
        strength.style.color = "green";
    } else {
        strength.innerHTML = "Medium (Use uppercase, lowercase & number)";
        strength.style.color = "orange";
    }
}

/* PASSWORD MATCH */
function checkMatch() {
    var pass = document.getElementById("new_password").value;
    var confirm = document.getElementById("confirm_password").value;
    var match = document.getElementById("match");

    if (pass === confirm) {
        match.innerHTML = "Passwords Match";
        match.style.color = "green";
    } else {
        match.innerHTML = "Passwords Do Not Match";
        match.style.color = "red";
    }
}

