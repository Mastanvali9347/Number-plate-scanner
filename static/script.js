// ================= BASE URL =================
const API = "http://127.0.0.1:8000";

// ================= ELEMENTS =================
const loginOverlay = document.getElementById("loginOverlay");
const loginBtn = document.getElementById("loginBtn");
const logoutBtn = document.getElementById("logoutBtn");
const usernameInput = document.getElementById("username");
const passwordInput = document.getElementById("password");

const themeToggle = document.getElementById("themeToggle");
const body = document.body;

const pages = {
  home: document.getElementById("homePage"),
  history: document.getElementById("historyPage"),
  profile: document.getElementById("profilePage")
};

const navLinks = document.querySelectorAll(".nav-link");

const fileInput = document.getElementById("fileInput");
const selectBtn = document.getElementById("selectBtn");
const uploadBtn = document.getElementById("uploadBtn");
const preview = document.getElementById("preview");
const previewImg = document.getElementById("previewImg");
const removeBtn = document.getElementById("removeBtn");
const scanBtn = document.getElementById("scanBtn");

const processing = document.getElementById("processing");
const details = document.getElementById("details");
const scanAnother = document.getElementById("scanAnother");
const downloadBtn = document.getElementById("downloadBtn");

const historyList = document.getElementById("historyList");
const profileUsername = document.getElementById("profileUsername");

// Vehicle fields
const fields = {
  reg_number: document.getElementById("reg_number"),
  owner: document.getElementById("owner"),
  model: document.getElementById("model"),
  fuel: document.getElementById("fuel"),
  reg_date: document.getElementById("reg_date"),
  vehicle_class: document.getElementById("vehicle_class"),
  color: document.getElementById("color")
};

// ================= STATE =================
let lastVehicleData = null;

// ================= INIT =================
loginOverlay.style.display = "grid";

// ================= LOGIN (REAL API) =================
loginBtn.addEventListener("click", async () => {
  const username = usernameInput.value.trim();
  const password = passwordInput.value.trim();

  if (!username || !password) {
    alert("⚠ Enter username and password");
    return;
  }

  try {
    const res = await fetch(`${API}/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ username, password })
    });

    const data = await res.json();

    if (!res.ok) {
      alert(data.error || "Login failed");
      return;
    }

    profileUsername.textContent = data.username;
    loginOverlay.style.display = "none";
    showPage("home");

  } catch (err) {
    alert("❌ Server error");
  }
});

// ================= LOGOUT =================
logoutBtn.addEventListener("click", () => {
  location.reload(); // clears session visually
});

// ================= THEME =================
themeToggle.onclick = () => {
  body.classList.toggle("dark");
  themeToggle.textContent = body.classList.contains("dark") ? "☀️" : "🌙";
};

// ================= NAVIGATION =================
navLinks.forEach(link => {
  link.addEventListener("click", e => {
    e.preventDefault();
    navLinks.forEach(l => l.classList.remove("active"));
    link.classList.add("active");
    showPage(link.dataset.page);
    if (link.dataset.page === "profile") loadProfile();
  });
});

function showPage(page) {
  Object.values(pages).forEach(p => p.classList.add("hidden"));
  pages[page].classList.remove("hidden");
}

// ================= IMAGE UPLOAD =================
selectBtn.onclick = () => fileInput.click();
uploadBtn.onclick = () => fileInput.click();

fileInput.onchange = () => {
  const file = fileInput.files[0];
  if (!file) return;
  previewImg.src = URL.createObjectURL(file);
  preview.classList.remove("hidden");
};

removeBtn.onclick = () => {
  fileInput.value = "";
  preview.classList.add("hidden");
  details.classList.add("hidden");
};

// ================= SCAN (REAL OCR API) =================
scanBtn.addEventListener("click", async () => {
  if (!fileInput.files.length) {
    alert("Select an image first");
    return;
  }

  const formData = new FormData();
  formData.append("image", fileInput.files[0]);

  processing.classList.remove("hidden");
  details.classList.add("hidden");

  try {
    const res = await fetch(`${API}/scan`, {
      method: "POST",
      credentials: "include",
      body: formData
    });

    const data = await res.json();
    processing.classList.add("hidden");

    if (!res.ok) {
      alert(data.error || "Scan failed");
      return;
    }

    if (!data.vehicle_details) {
      alert(data.message || "No plate detected");
      return;
    }

    lastVehicleData = data.vehicle_details;

    Object.keys(fields).forEach(k => {
      fields[k].textContent = data.vehicle_details[k] || "-";
    });

    details.classList.remove("hidden");
    addHistory(data.plate_number);

  } catch (err) {
    processing.classList.add("hidden");
    alert("❌ Server error");
  }
});

// ================= HISTORY =================
function addHistory(plate) {
  const div = document.createElement("div");
  div.className = "card";
  div.innerHTML = `<b>${plate}</b><br><small>${new Date().toLocaleString()}</small>`;
  historyList.prepend(div);
}

// ================= PROFILE =================
async function loadProfile() {
  try {
    const res = await fetch(`${API}/profile`, {
      credentials: "include"
    });
    const data = await res.json();
    profileUsername.textContent = data.username;
  } catch {
    alert("Failed to load profile");
  }
}

// ================= DOWNLOAD PDF =================
downloadBtn.addEventListener("click", async () => {
  if (!lastVehicleData) return;

  const res = await fetch(`${API}/download-report`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ vehicle_details: lastVehicleData })
  });

  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "vehicle_report.pdf";
  a.click();
});

// ================= SCAN AGAIN =================
scanAnother.onclick = () => {
  details.classList.add("hidden");
  preview.classList.add("hidden");
  fileInput.value = "";
};
