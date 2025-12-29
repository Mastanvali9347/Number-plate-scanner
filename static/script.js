const API_BASE = "http://127.0.0.1:8000";

const body = document.body;
const navLinks = document.querySelectorAll(".nav-link");

const homePage = document.getElementById("homePage");
const historyPage = document.getElementById("historyPage");
const profilePage = document.getElementById("profilePage");

const themeToggle = document.getElementById("themeToggle");

const loginOverlay = document.getElementById("loginOverlay");
const loginBtn = document.getElementById("loginBtn");
const logoutBtn = document.getElementById("logoutBtn");
const usernameInput = document.getElementById("username");
const passwordInput = document.getElementById("password");

const dropArea = document.getElementById("dropArea");
const fileInput = document.getElementById("fileInput");
const selectBtn = document.getElementById("selectBtn");
const uploadBtn = document.getElementById("uploadBtn");
const preview = document.getElementById("preview");
const previewImg = document.getElementById("previewImg");
const removeBtn = document.getElementById("removeBtn");
const scanBtn = document.getElementById("scanBtn");

const processing = document.getElementById("processing");
const details = document.getElementById("details");

const regNumber = document.getElementById("reg_number");
const owner = document.getElementById("owner");
const model = document.getElementById("model");
const fuel = document.getElementById("fuel");
const regDate = document.getElementById("reg_date");
const vehicleClass = document.getElementById("vehicle_class");
const color = document.getElementById("color");

const scanAnother = document.getElementById("scanAnother");
const downloadBtn = document.getElementById("downloadBtn");
const historyList = document.getElementById("historyList");
const profileUsername = document.getElementById("profileUsername");

const getAuthHeaders = () => ({
  Authorization: "Bearer " + localStorage.getItem("token")
});

themeToggle.onclick = () => {
  body.classList.toggle("dark");
  body.classList.toggle("light");
  themeToggle.textContent = body.classList.contains("dark") ? "☀" : "🌙";
};

loginBtn.onclick = async () => {
  const username = usernameInput.value.trim();
  const password = passwordInput.value.trim();
  if (!username || !password) return alert("Enter username and password");

  try {
    const res = await fetch(`${API_BASE}/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password })
    });

    const data = await res.json();
    if (!res.ok) return alert(data.error || "Login failed");

    localStorage.setItem("token", data.token);
    profileUsername.textContent = data.username;
    loginOverlay.classList.add("hidden");
  } catch {
    alert("Server error");
  }
};

(async () => {
  const token = localStorage.getItem("token");
  if (!token) return;

  try {
    const res = await fetch(`${API_BASE}/profile`, {
      headers: getAuthHeaders()
    });
    if (!res.ok) return;

    const data = await res.json();
    profileUsername.textContent = data.username;
    loginOverlay.classList.add("hidden");
  } catch {}
})();

logoutBtn.onclick = () => {
  localStorage.removeItem("token");
  location.reload();
};

navLinks.forEach(link => {
  link.onclick = () => {
    navLinks.forEach(l => l.classList.remove("active"));
    link.classList.add("active");

    homePage.classList.add("hidden");
    historyPage.classList.add("hidden");
    profilePage.classList.add("hidden");

    if (link.dataset.page === "home") homePage.classList.remove("hidden");
    if (link.dataset.page === "history") loadHistory();
    if (link.dataset.page === "profile") profilePage.classList.remove("hidden");
  };
});

selectBtn.onclick = () => fileInput.click();
uploadBtn.onclick = () => fileInput.click();

fileInput.onchange = () => showPreview(fileInput.files[0]);

dropArea.ondragover = e => e.preventDefault();
dropArea.ondrop = e => {
  e.preventDefault();
  showPreview(e.dataTransfer.files[0]);
};

function showPreview(file) {
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    previewImg.src = reader.result;
    preview.classList.remove("hidden");
    dropArea.classList.add("hidden");
  };
  reader.readAsDataURL(file);
}

removeBtn.onclick = () => {
  preview.classList.add("hidden");
  dropArea.classList.remove("hidden");
  fileInput.value = "";
};

scanBtn.onclick = async () => {
  const file = fileInput.files[0];
  if (!file) return alert("Select an image");

  preview.classList.add("hidden");
  details.classList.add("hidden");
  processing.classList.remove("hidden");

  const formData = new FormData();
  formData.append("image", file);

  try {
    const res = await fetch(`${API_BASE}/scan`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: formData
    });

    const data = await res.json();
    if (!res.ok) {
      alert(data.error || "Scan failed");
      preview.classList.remove("hidden");
      return;
    }

    showResults(data);
  } catch {
    alert("Server error");
    preview.classList.remove("hidden");
  } finally {
    processing.classList.add("hidden");
  }
};

function showResults(data) {
  regNumber.textContent = data.registration_number;
  owner.textContent = data.owner;
  model.textContent = data.model;
  fuel.textContent = data.fuel;
  regDate.textContent = data.registration_date;
  vehicleClass.textContent = data.vehicle_class;
  color.textContent = data.color;
  details.classList.remove("hidden");
}

scanAnother.onclick = () => {
  details.classList.add("hidden");
  dropArea.classList.remove("hidden");
  fileInput.value = "";
};

async function loadHistory() {
  historyPage.classList.remove("hidden");

  try {
    const res = await fetch(`${API_BASE}/history`, {
      headers: getAuthHeaders()
    });

    const history = await res.json();
    historyList.innerHTML = "";

    if (!Array.isArray(history) || history.length === 0) {
      historyList.innerHTML = "<p class='muted'>No scans yet</p>";
      return;
    }

    history.forEach(h => {
      const div = document.createElement("div");
      div.className = "card";
      div.innerHTML = `<b>${h.registration_number}</b><br><small class="muted">${h.time}</small>`;
      historyList.appendChild(div);
    });
  } catch {
    historyList.innerHTML = "<p class='muted'>Unable to load history</p>";
  }
}

downloadBtn.onclick = async () => {
  const payload = {
    "Registration Number": regNumber.textContent,
    "Owner": owner.textContent,
    "Model": model.textContent,
    "Fuel": fuel.textContent,
    "Registration Date": regDate.textContent,
    "Vehicle Class": vehicleClass.textContent,
    "Color": color.textContent
  };

  const res = await fetch(`${API_BASE}/download-report`, {
    method: "POST",
    headers: {
      ...getAuthHeaders(),
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });

  const blob = await res.blob();
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "vehicle_report.pdf";
  link.click();
};
