document.addEventListener("DOMContentLoaded", () => {
  const dropZone = document.getElementById("drop-zone");
  const fileInput = document.getElementById("file-input");
  const fileNameEl = document.getElementById("file-name");
  const journalSelect = document.getElementById("journal-select");
  const journalPreview = document.getElementById("journal-preview");
  const previewContent = document.getElementById("preview-content");
  const emailInput = document.getElementById("email-input");
  const form = document.getElementById("format-form");
  const submitBtn = document.getElementById("submit-btn");
  const loading = document.getElementById("loading");
  const result = document.getElementById("result");
  const resultContent = document.getElementById("result-content");
  const resultDismiss = document.getElementById("result-dismiss");

  let selectedFile = null;

  // ---------- Load journals ----------
  async function loadJournals() {
    try {
      const res = await fetch("/api/journals");
      const data = await res.json();
      data.journals.forEach((j) => {
        const opt = document.createElement("option");
        opt.value = j.id;
        opt.textContent = j.name;
        journalSelect.appendChild(opt);
      });
    } catch (err) {
      console.error("Failed to load journals:", err);
    }
  }
  loadJournals();

  // ---------- Journal preview ----------
  journalSelect.addEventListener("change", async () => {
    const id = journalSelect.value;
    if (!id) {
      journalPreview.classList.add("hidden");
      return;
    }
    try {
      const res = await fetch(`/api/journals/${id}`);
      const cfg = await res.json();
      renderPreview(cfg);
      journalPreview.classList.remove("hidden");
    } catch (err) {
      console.error("Failed to load journal config:", err);
    }
  });

  function renderPreview(cfg) {
    const layout = cfg.page_layout || {};
    const fonts = cfg.fonts || {};
    const cite = cfg.citation_style || {};
    const ref = cfg.reference_style || {};
    const tables = cfg.tables || {};
    const figures = cfg.figures || {};
    const abs = cfg.abstract || {};

    const rows = [
      ["Page Size", (layout.page_size || "").toUpperCase()],
      ["Margins", `${layout.margins?.top}"/${layout.margins?.bottom}"/${layout.margins?.left}"/${layout.margins?.right}"`],
      ["Line Spacing", layout.line_spacing],
      ["Body Font", `${fonts.body?.family || "—"} ${fonts.body?.size || ""}pt`],
      ["Citation Style", cite.type ? cite.type.replace(/_/g, " ") : "—"],
      ["Citation Format", cite.format || "—"],
      ["Reference Numbering", ref.numbering || "—"],
      ["Table Captions", `${tables.prefix || "Table"} (${tables.caption_position || "above"}), ${tables.numbering_format || "arabic"}`],
      ["Figure Captions", `${figures.prefix || "Figure"} (${figures.caption_position || "below"})`],
      ["Abstract Max Words", abs.max_words || "—"],
    ];

    previewContent.innerHTML = rows
      .map(
        ([label, value]) =>
          `<div class="preview-row"><span class="preview-label">${label}</span><span class="preview-value">${value}</span></div>`
      )
      .join("");
  }

  // ---------- Drag and drop ----------
  const VALID_EXT = [".doc", ".docx"];

  function validFile(file) {
    const name = file.name.toLowerCase();
    return VALID_EXT.some((ext) => name.endsWith(ext));
  }

  function showFile(file) {
    selectedFile = file;
    fileNameEl.textContent = file.name;
    fileNameEl.classList.remove("hidden");
    dropZone.classList.add("has-file");
  }

  dropZone.addEventListener("click", () => fileInput.click());
  dropZone.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      fileInput.click();
    }
  });

  fileInput.addEventListener("change", () => {
    if (fileInput.files.length > 0) {
      const file = fileInput.files[0];
      if (validFile(file)) {
        showFile(file);
      } else {
        alert("Please select a .doc or .docx file.");
        fileInput.value = "";
      }
    }
  });

  dropZone.addEventListener("dragenter", (e) => {
    e.preventDefault();
    dropZone.classList.add("drag-over");
  });

  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("drag-over");
  });

  dropZone.addEventListener("dragleave", (e) => {
    e.preventDefault();
    dropZone.classList.remove("drag-over");
  });

  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("drag-over");
    const file = e.dataTransfer.files[0];
    if (file && validFile(file)) {
      showFile(file);
    } else {
      alert("Please drop a .doc or .docx file.");
    }
  });

  // ---------- Form submission ----------
  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    if (!selectedFile) {
      alert("Please select a manuscript file.");
      return;
    }
    if (!journalSelect.value) {
      alert("Please select a target journal.");
      return;
    }
    const email = emailInput.value.trim();
    if (!email || !emailInput.checkValidity()) {
      alert("Please enter a valid email address.");
      return;
    }

    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("journal_id", journalSelect.value);
    formData.append("email", email);

    showLoading(true);
    hideResult();

    try {
      const res = await fetch("/api/format", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();

      if (res.ok && data.success) {
        showSuccess(data);
      } else {
        showError(data.detail || data.message || "An unexpected error occurred.");
      }
    } catch (err) {
      showError("Network error. Please try again.");
    } finally {
      showLoading(false);
    }
  });

  // ---------- Result display ----------
  function showLoading(visible) {
    loading.classList.toggle("hidden", !visible);
    submitBtn.disabled = visible;
  }

  function hideResult() {
    result.classList.add("hidden");
    form.classList.remove("hidden");
  }

  function showSuccess(data) {
    let html = `<div class="result-success"><h3>Success</h3><p>${data.message}</p>`;

    if (data.stats) {
      html += `<div class="stats-grid">`;
      html += `<div class="stat"><span class="stat-num">${data.stats.citations_reformatted}/${data.stats.citations_found}</span><span class="stat-label">Citations</span></div>`;
      html += `<div class="stat"><span class="stat-num">${data.stats.references_reformatted}/${data.stats.references_found}</span><span class="stat-label">References</span></div>`;
      html += `<div class="stat"><span class="stat-num">${data.stats.tables_found}</span><span class="stat-label">Tables</span></div>`;
      html += `<div class="stat"><span class="stat-num">${data.stats.figures_found}</span><span class="stat-label">Figures</span></div>`;
      html += `</div>`;
    }

    if (data.warnings && data.warnings.length > 0) {
      html += `<div class="result-warnings"><h4>Warnings</h4><ul>`;
      data.warnings.forEach((w) => {
        html += `<li>${w.message}</li>`;
      });
      html += `</ul></div>`;
    }

    html += `</div>`;
    resultContent.innerHTML = html;
    form.classList.add("hidden");
    result.classList.remove("hidden");
  }

  function showError(message) {
    resultContent.innerHTML = `<div class="result-error"><h3>Error</h3><p>${message}</p></div>`;
    form.classList.add("hidden");
    result.classList.remove("hidden");
  }

  resultDismiss.addEventListener("click", () => {
    hideResult();
    selectedFile = null;
    fileInput.value = "";
    fileNameEl.classList.add("hidden");
    dropZone.classList.remove("has-file");
  });
});
