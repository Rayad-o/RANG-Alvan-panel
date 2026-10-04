const token = localStorage.getItem("access_token");
const user = JSON.parse(localStorage.getItem("user") || "null");

if (!token || !user) {
    window.location.href = "index.html";
}

document.getElementById("welcomeText").textContent = `خوش آمدید، ${user.full_name}`;

document.getElementById("logoutBtn").addEventListener("click", function (e) {
    e.preventDefault();
    localStorage.removeItem("access_token");
    localStorage.removeItem("user");
    window.location.href = "index.html";
});
