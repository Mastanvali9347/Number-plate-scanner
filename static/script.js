// ===================== ELEMENTS =====================
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
  profile: document.getElementById("profilePage"),
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
  color: document.getElementById("color"),
};

// ===================== STATE =====================
let isLoggedIn = false;
let currentUser = "";
let history = [];

// ===================== INIT =====================
loginOverlay.style.display = "grid";

// ===================== LOGIN =====================
loginBtn.addEventListener("click", () => {
  const username = usernameInput.value.trim();
  const password = passwordInput.value.trim();

  if (!username || !password) {
    alert("⚠ Please enter username and password");
    return;
  }

  isLoggedIn = true;
  currentUser = username;
  profileUsername.textContent = username;

  loginOverlay.style.display = "none";
  alert(`✅ Welcome, ${username}`);
});

// ===================== LOGOUT =====================
logoutBtn.addEventListener("click", () => {
  isLoggedIn = false;
  currentUser = "";
  usernameInput.value = "";
  passwordInput.value = "";

  loginOverlay.style.display = "grid";
  showPage("home");
});

// ===================== NAVIGATION =====================
navLinks.forEach(link => {
  link.addEventListener("click", e => {
    e.preventDefault();
    if (!isLoggedIn) {
      alert("🔐 Please login first");
      return;
    }

    navLinks.forEach(l => l.classList.remove("active"));
    link.classList.add("active");

    showPage(link.dataset.page);
  });
});

function showPage(page) {
  Object.values(pages).forEach(p => p.classList.add("hidden"));
  pages[page].classList.remove("hidden");
}

// ===================== THEME TOGGLE =====================
themeToggle.addEventListener("click", () => {
  body.classList.toggle("dark");
  themeToggle.textContent = body.classList.contains("dark") ? "☀" : "🌙";
});

// ===================== IMAGE UPLOAD =====================
selectBtn.addEventListener("click", () => fileInput.click());
uploadBtn.addEventListener("click", () => fileInput.click());

fileInput.addEventListener("change", () => {
  const file = fileInput.files[0];
  if (!file) return;

  previewImg.src = URL.createObjectURL(file);
  preview.classList.remove("hidden");
  details.classList.add("hidden");
});

// ===================== REMOVE IMAGE =====================
removeBtn.addEventListener("click", () => {
  preview.classList.add("hidden");
  previewImg.src = "";
  fileInput.value = "";
});

// ===================== SCAN (DEMO LOGIC) =====================
scanBtn.addEventListener("click", () => {
  processing.classList.remove("hidden");
  details.classList.add("hidden");

  setTimeout(() => {
    processing.classList.add("hidden");

    // Demo vehicle data
    const data = {
      reg_number: "AP09AB1234",
      owner: currentUser,
      model: "Hyundai Creta",
      fuel: "Petrol",
      reg_date: "12-06-2021",
      vehicle_class: "LMV",
      color: "White",
    };

    Object.keys(fields).forEach(key => {
      fields[key].textContent = data[key];
    });

    details.classList.remove("hidden");
    saveToHistory(data);
  }, 2500);
});

// ===================== HISTORY =====================
function saveToHistory(data) {
  history.push({
    ...data,
    time: new Date().toLocaleString(),
  });

  renderHistory();
}

function renderHistory() {
  historyList.innerHTML = "";

  history.forEach(item => {
    const div = document.createElement("div");
    div.className = "card";
    div.innerHTML = `
      <b>${item.reg_number}</b>
      <p class="muted">${item.model} • ${item.time}</p>
    `;
    historyList.appendChild(div);
  });
}
renderHistory();