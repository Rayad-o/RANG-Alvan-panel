const API_URL = "http://127.0.0.1:8000";

document.getElementById('loginForm').addEventListener('submit', async function (e) {
    e.preventDefault();

    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const errorMessage = document.getElementById('errorMessage');

    errorMessage.textContent = '';

    try {
        const response = await fetch(`${API_URL}/auth/login`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();

        if (!response.ok) {
            errorMessage.textContent = data.detail || "ورود ناموفق بود";
            return;
        }

        localStorage.setItem("access_token", data.access_token);
        localStorage.setItem("user", JSON.stringify(data.user));

        window.location.href = "dashboard.html";

    } catch (error) {
        errorMessage.textContent = "خطا در اتصال به سرور. مطمئن شو Backend روشن است.";
        console.error(error);
    }
});

