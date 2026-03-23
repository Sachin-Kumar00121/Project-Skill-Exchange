// for theme Toggle 

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

/* CUSTOM CONFIRM FUNCTION */

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
 
// for dashboard  
    const notifyBtn = document.getElementById('notify-btn');
    const notifyDropdown = document.getElementById('notify-dropdown');
    const profileBtn = document.getElementById('profile-btn');
    const profileDropdown = document.getElementById('profile-dropdown');
    
    // SIDEBAR ID FIXED HERE FOR TOGGLE
    const sidebar = document.getElementById('appSidebar');
    const mainContent = document.getElementById('appMainContent');
    const toggleBtn = document.getElementById('toggle-sidebar');

    notifyBtn.addEventListener('click', (e) => { e.stopPropagation(); 
         notifyDropdown.classList.toggle('show');
         profileDropdown.classList.remove('show'); });

    profileBtn.addEventListener('click', (e) => { e.stopPropagation();
        profileDropdown.classList.toggle('show'); 
        notifyDropdown.classList.remove('show'); });
        
    window.addEventListener('click', () => { notifyDropdown.classList.remove('show');
         profileDropdown.classList.remove('show'); });

    // SIDEBAR TOGGLE EVENT
    toggleBtn.addEventListener('click', () => {
        sidebar.classList.toggle('collapsed');
        mainContent.classList.toggle('expanded');
        localStorage.setItem('sidebarState', sidebar.classList.contains('collapsed'));
    });

    if(localStorage.getItem('sidebarState') === 'true') {
        sidebar.classList.add('collapsed');
        mainContent.classList.add('expanded');
    }

// For Profile Section

     function toggleEditMode() {
        const viewSection = document.getElementById('profile-view-section');
        const editSection = document.getElementById('profile-edit-section');
        if (viewSection.style.display === 'none') {
            viewSection.style.display = 'block';
            editSection.style.display = 'none';
        } else {
            viewSection.style.display = 'none';
            editSection.style.display = 'block';
        }
    }

    function copyProfileLink(link) {
        navigator.clipboard.writeText(link).then(() => {
            const btn = document.getElementById('copyBtn');
            const originalText = btn.innerHTML;
            btn.innerHTML = '<i class="fa-solid fa-check-double"></i> Copied!';
            btn.classList.add('copied-success');
            setTimeout(() => { 
                btn.innerHTML = originalText; 
                btn.classList.remove('copied-success');
            }, 2500);
        });
    }

