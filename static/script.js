// Make sure DOM is ready
document.addEventListener("DOMContentLoaded", () => {
  // -------------------------------
  // DOM Elements
  // -------------------------------
  const dropArea = document.getElementById("dropArea");
  const fileInput = document.getElementById("fileInput");
  const selectBtn = document.getElementById("selectBtn");
  const preview = document.getElementById("preview");
  const previewImg = document.getElementById("previewImg");
  const scanBtn = document.getElementById("scanBtn");
  const processing = document.getElementById("processing");
  const details = document.getElementById("details");
  const fields = document.getElementById("fields");
  const removeBtn = document.getElementById("removeBtn");
  const progressBar = document.getElementById("progressBar");
  const s1 = document.getElementById("s1");
  const s2 = document.getElementById("s2");
  const s3 = document.getElementById("s3");
  const downloadBtn = document.getElementById("downloadBtn");
  const scanAnother = document.getElementById("scanAnother");

  let selectedFile = null;

  // -------------------------------
  // Helpers
  // -------------------------------
  const show = (el) => el && el.classList.remove("hidden");
  const hide = (el) => el && el.classList.add("hidden");

  // Normalize plate → "RJ14DT3249"
  const normalizePlate = (p) =>
    p ? String(p).replace(/[^A-Z0-9]/gi, "").toUpperCase() : "";

  // -------------------------------
  // File Selection
  // -------------------------------
  selectBtn.onclick = () => fileInput.click();

  fileInput.onchange = (e) => {
    selectedFile = e.target.files[0];
    if (selectedFile) {
      showPreview(selectedFile);
    }
  };

  dropArea.onclick = () => fileInput.click();

  dropArea.ondragover = (e) => {
    e.preventDefault();
    dropArea.style.borderColor = "rgba(255,255,255,0.14)";
  };

  dropArea.ondragleave = () => {
    dropArea.style.borderColor = "rgba(255,255,255,0.06)";
  };

  dropArea.ondrop = (e) => {
    e.preventDefault();
    dropArea.style.borderColor = "rgba(255,255,255,0.06)";
    selectedFile = e.dataTransfer.files[0];
    if (selectedFile) {
      showPreview(selectedFile);
    }
  };

  function showPreview(file) {
    previewImg.src = URL.createObjectURL(file);
    show(preview);
    hide(details);
    hide(processing);
  }

  // -------------------------------
  // Remove Image
  // -------------------------------
  removeBtn.onclick = () => {
    selectedFile = null;
    fileInput.value = "";
    previewImg.src = "";
    hide(preview);
    hide(details);
    hide(processing);
    fields.innerHTML = "";
  };

  // -------------------------------
  // Scan Button → Upload to backend
  // -------------------------------
  scanBtn.onclick = async () => {
    if (!selectedFile) {
      alert("Please select an image first!");
      return;
    }

    hide(preview);
    hide(details);
    show(processing);
    startProgressAnimation();

    const formData = new FormData();
    formData.append("image", selectedFile);

    try {
      const res = await fetch("/scan", {
        method: "POST",
        body: formData
      });

      const data = await res.json();
      console.log("SCAN RESPONSE:", data);

      setTimeout(() => {
        hide(processing);
        showDetails(data);
      }, 1800);
    } catch (err) {
      hide(processing);
      alert("Server error: " + err.message);
    }
  };

  // -------------------------------
  // Progress Animation UI
  // -------------------------------
  function startProgressAnimation() {
    progressBar.style.width = "0%";
    s1.textContent = s2.textContent = s3.textContent = "○";

    setTimeout(() => {
      s1.textContent = "✔";
      progressBar.style.width = "30%";
    }, 500);

    setTimeout(() => {
      s2.textContent = "✔";
      progressBar.style.width = "65%";
    }, 1000);

    setTimeout(() => {
      s3.textContent = "✔";
      progressBar.style.width = "100%";
    }, 1500);
  }

  // -------------------------------
  // Show Details from Backend
  // -------------------------------
  function showDetails(data) {
    fields.innerHTML = "";

    // 1) Backend error
    if (data.error) {
      fields.innerHTML = `
        <p style="color:#ff6a6a;font-size:17px;margin-top:10px;">
          ❌ Server error: <b>${data.error}</b>
        </p>`;
      show(details);
      return;
    }

    const rawPlate = data.plate_number || "";
    const normalizedPlate = normalizePlate(rawPlate);

    // 2) Vehicle details found from database
    if (data.vehicle_details) {
      const v = data.vehicle_details;

      addField("🔖", "Registration Number", v["Registration Number"] || normalizedPlate);
      addField("👤", "Owner Name", v["Owner Name"] || "—");
      addField("🚗", "Vehicle Model", v["Vehicle Model"] || "—");
      addField("🛢️", "Fuel Type", v["Fuel Type"] || "—");
      addField("📅", "Registration Date", v["Registration Date"] || "—");
      addField("🚙", "Vehicle Class", v["Vehicle Class"] || "—");
      addField("🎨", "Color", v["Color"] || "—");

      show(details);
      return;
    }

    // 3) Plate detected, but NOT in database
    if (normalizedPlate) {
      fields.innerHTML = `
        <p style="color:#ff6a6a;font-size:17px;margin-top:10px;">
          ❌ Plate detected: <b>${normalizedPlate}</b><br>
          No record found in database.
        </p>`;
      show(details);
      return;
    }

    // 4) No plate detected at all
    const ocrText = Array.isArray(data.ocr_texts)
      ? data.ocr_texts.join(", ")
      : "None";

    fields.innerHTML = `
      <p style="color:#ff6a6a;font-size:17px;margin-top:10px;">
        ❌ No plate detected.<br>
        OCR Text: ${ocrText}
      </p>`;
    show(details);
  }

  // -------------------------------
  function addField(icon, label, value) {
    const el = document.createElement("div");
    el.className = "field";
    el.innerHTML = `
      <div class="icon">${icon}</div>
      <div class="meta">
        <div class="label">${label}</div>
        <div class="value">${value ?? "—"}</div>
      </div>`;
    fields.appendChild(el);
  }

  // -------------------------------
  // Download JSON
  // -------------------------------
  downloadBtn.onclick = () => {
    const items = Array.from(fields.querySelectorAll(".field")).map((f) => ({
      label: f.querySelector(".label").textContent,
      value: f.querySelector(".value").textContent
    }));

    if (!items.length) {
      alert("No details to download.");
      return;
    }

    const blob = new Blob([JSON.stringify(items, null, 2)], {
      type: "application/json"
    });

    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "vehicle-details.json";
    a.click();

    alert("✅ Vehicle details downloaded successfully!");
  };

  // -------------------------------
  // Scan another
  // -------------------------------
  scanAnother.onclick = () => {
    hide(details);
    if (selectedFile) {
      show(preview);
    } else {
      hide(preview);
    }
  };
});
