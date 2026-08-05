// Captain Thermo frontend — vanilla JS, talks to /api/*

const API = ""; // same origin

// ---------- Passcode flow ----------
// If the backend has APP_PASSCODE set, prompt for it and store in localStorage.
let passcode = localStorage.getItem("ct_passcode") || "";

async function ensurePasscode() {
  try {
    const r = await fetch(API + "/api/config");
    const { passcode_required } = await r.json();
    if (!passcode_required) return;
    if (!passcode) {
      const entered = prompt("Enter the Captain Thermo access code (ask Prof Leonard):");
      if (entered) {
        passcode = entered.trim();
        localStorage.setItem("ct_passcode", passcode);
      }
    }
  } catch (e) {
    console.error("config check failed", e);
  }
}
ensurePasscode();

// ---------- Per-browser client id ----------
// Rate limits are counted per client id rather than per IP. On campus wifi
// every student shares a handful of NAT'd public IPs, so IP-keyed limits
// would make one student's usage eat the whole cohort's quota.
// This is a fairness mechanism, not a security one — the passcode is the
// actual gate, and a much higher per-IP ceiling still backstops abuse.
let clientId = localStorage.getItem("ct_client_id") || "";
if (!clientId) {
  clientId =
    (crypto.randomUUID && crypto.randomUUID()) ||
    `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  localStorage.setItem("ct_client_id", clientId);
}

function authHeaders(extra = {}) {
  const h = { "Content-Type": "application/json", ...extra };
  if (passcode) h["X-Passcode"] = passcode;
  h["X-Client-Id"] = clientId;
  return h;
}

async function apiFetch(url, options = {}) {
  const resp = await fetch(url, {
    ...options,
    headers: authHeaders(options.headers || {}),
  });
  if (resp.status === 401) {
    localStorage.removeItem("ct_passcode");
    passcode = "";
    alert("Access code was rejected. Refresh to try again.");
    throw new Error("Unauthorized");
  }
  if (resp.status === 429) {
    const body = await resp.json().catch(() => ({}));
    throw new Error(body.detail || "Rate limit hit — please slow down.");
  }
  if (!resp.ok && resp.headers.get("content-type")?.includes("json")) {
    const body = await resp.json().catch(() => ({}));
    throw new Error(body.detail || `Server error (${resp.status})`);
  }
  if (!resp.ok) {
    throw new Error(`Server error (${resp.status})`);
  }
  return resp;
}

// ---------- Tab switching ----------
document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("tab-active"));
    btn.classList.add("tab-active");
    document.querySelectorAll(".tab-panel").forEach((p) => p.classList.add("hidden"));
    document.getElementById("tab-" + btn.dataset.tab).classList.remove("hidden");
  });
});

// ---------- Populate topic dropdowns ----------
async function loadTopics() {
  try {
    const r = await fetch(API + "/api/topics");
    const { topics } = await r.json();
    const opts = Object.entries(topics)
      .map(([code, name]) => `<option value="${code}">${code} — ${name}</option>`)
      .join("");
    document.getElementById("practice-topic").innerHTML = opts;
    document.getElementById("cards-topic").innerHTML = opts;
  } catch (e) {
    console.error("Could not load topics:", e);
  }
}
loadTopics();

// ---------- Render helpers ----------
function renderMarkdown(text) {
  // marked.parse handles basic MD; MathJax typesets after.
  return marked.parse(text);
}

function typeset(el) {
  if (window.MathJax && window.MathJax.typesetPromise) {
    window.MathJax.typesetPromise([el]).catch(() => {});
  }
}

// ---------- Tutor (streaming chat) ----------
const chatLog = document.getElementById("chat-log");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const messages = [];

// Only auto-scroll if the user is already near the bottom — so if they scrolled
// up to re-read something, we don't yank them back down while Claude streams.
function isNearBottom(el, slack = 80) {
  return el.scrollHeight - el.scrollTop - el.clientHeight < slack;
}
function scrollToBottom(el) {
  el.scrollTop = el.scrollHeight;
}

function addBubble(role, text) {
  const wrap = document.createElement("div");
  wrap.className = role === "user" ? "chat-user rounded-lg p-3 ml-12" : "chat-assistant rounded-lg p-3 mr-12";
  const label = document.createElement("div");
  label.className = "text-xs text-gray-400 mb-1";
  label.textContent = role === "user" ? "You" : "Captain Thermo";
  const body = document.createElement("div");
  body.className = "prose-cap";
  body.innerHTML = renderMarkdown(text);
  wrap.appendChild(label);
  wrap.appendChild(body);
  chatLog.appendChild(wrap);
  scrollToBottom(chatLog);
  typeset(body);
  return body;
}

// Enter submits; Shift+Enter inserts a newline. IME composition (é, Chinese, etc.) bypassed.
chatInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
    e.preventDefault();
    chatForm.requestSubmit();
  }
});

chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = chatInput.value.trim();
  if (!text) return;
  chatInput.value = "";
  addBubble("user", text);
  messages.push({ role: "user", content: text });

  const assistantBody = addBubble("assistant", "…");
  let acc = "";

  try {
    const resp = await apiFetch(API + "/api/chat", {
      method: "POST",
      body: JSON.stringify({ messages }),
    });
    if (!resp.ok || !resp.body) {
      assistantBody.textContent = "Network error.";
      return;
    }
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const lines = buf.split("\n\n");
      buf = lines.pop();
      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        try {
          const data = JSON.parse(line.slice(6));
          if (data.text) {
            const shouldFollow = isNearBottom(chatLog);
            acc += data.text;
            assistantBody.innerHTML = renderMarkdown(acc);
            if (shouldFollow) scrollToBottom(chatLog);
          }
          if (data.done) {
            typeset(assistantBody);
            if (isNearBottom(chatLog)) scrollToBottom(chatLog);
            messages.push({ role: "assistant", content: acc });
          }
          if (data.error) {
            assistantBody.textContent = "Error: " + data.error;
          }
        } catch {}
      }
    }
  } catch (err) {
    assistantBody.textContent = "Error: " + err.message;
  }
});

// ---------- Practice ----------
const practiceForm = document.getElementById("practice-form");
const practiceOut = document.getElementById("practice-out");

practiceForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const topic = document.getElementById("practice-topic").value;
  const difficulty = document.getElementById("practice-difficulty").value;
  practiceOut.innerHTML = '<div class="text-gray-400 text-sm">Forging a new problem…</div>';
  try {
    const r = await apiFetch(API + "/api/generate", {
      method: "POST",
      body: JSON.stringify({ topic, difficulty }),
    });
    const p = await r.json();
    practiceOut.innerHTML = `
      <div class="bg-gray-800 rounded-lg p-4 mb-3">
        <div class="text-xs text-blue-300 mb-1">${p.topic} · ${p.difficulty}</div>
        <h3 class="font-semibold mb-2">${p.title}</h3>
        <div class="prose-cap">${renderMarkdown(p.statement)}</div>
      </div>
      <details class="bg-gray-800 rounded-lg p-4 mb-3">
        <summary class="cursor-pointer font-medium text-green-300">Show worked solution</summary>
        <div class="prose-cap mt-3">${renderMarkdown(p.solution)}</div>
        <div class="mt-3 pt-3 border-t border-gray-700">
          <div class="text-xs text-gray-400">Final answer</div>
          <div class="prose-cap">${renderMarkdown(p.final_answer)}</div>
        </div>
      </details>
      <details class="bg-gray-800 rounded-lg p-4">
        <summary class="cursor-pointer font-medium text-amber-300">Common mistakes to avoid</summary>
        <ul class="list-disc pl-5 mt-3 prose-cap text-sm space-y-1">
          ${p.common_mistakes.map((m) => `<li>${renderMarkdown(m)}</li>`).join("")}
        </ul>
      </details>
    `;
    typeset(practiceOut);
  } catch (err) {
    practiceOut.innerHTML = `<div class="text-red-400">Error: ${err.message}</div>`;
  }
});

// ---------- Grader ----------
const gradeForm = document.getElementById("grade-form");
const gradeOut = document.getElementById("grade-out");
const gradeImagesInput = document.getElementById("grade-images");
const gradeImagePreview = document.getElementById("grade-image-preview");

// Client-side resize: long edge -> MAX_EDGE, re-encode as JPEG.
// Opus 4.7 accepts up to 2576px on the long edge; 2000px is a comfortable
// sweet spot that keeps uploads small without losing handwriting clarity.
const MAX_EDGE = 2000;
const JPEG_QUALITY = 0.88;
let gradeImages = []; // [{ media_type, data, previewUrl }]

async function resizeImage(file) {
  const bitmap = await createImageBitmap(file);
  const scale = Math.min(1, MAX_EDGE / Math.max(bitmap.width, bitmap.height));
  const w = Math.round(bitmap.width * scale);
  const h = Math.round(bitmap.height * scale);
  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  canvas.getContext("2d").drawImage(bitmap, 0, 0, w, h);
  const blob = await new Promise((res) => canvas.toBlob(res, "image/jpeg", JPEG_QUALITY));
  const dataUrl = await new Promise((res) => {
    const reader = new FileReader();
    reader.onload = () => res(reader.result);
    reader.readAsDataURL(blob);
  });
  // dataUrl: "data:image/jpeg;base64,XXXX"
  const base64 = dataUrl.split(",", 2)[1];
  return { media_type: "image/jpeg", data: base64, previewUrl: URL.createObjectURL(blob) };
}

function renderImagePreviews() {
  gradeImagePreview.innerHTML = gradeImages
    .map(
      (img, i) => `
        <div class="relative">
          <img src="${img.previewUrl}" class="h-20 w-20 object-cover rounded border border-gray-700" />
          <button type="button" data-idx="${i}" class="remove-img absolute -top-2 -right-2 bg-red-600 hover:bg-red-500 rounded-full w-5 h-5 text-xs leading-none">×</button>
        </div>`
    )
    .join("");
  gradeImagePreview.querySelectorAll(".remove-img").forEach((btn) => {
    btn.addEventListener("click", () => {
      const idx = parseInt(btn.dataset.idx, 10);
      URL.revokeObjectURL(gradeImages[idx].previewUrl);
      gradeImages.splice(idx, 1);
      renderImagePreviews();
    });
  });
}

async function ingestFiles(fileList) {
  const files = Array.from(fileList || []).filter((f) => f.type.startsWith("image/"));
  if (!files.length) return;
  const room = Math.max(0, 8 - gradeImages.length);
  if (files.length > room) {
    alert(`You can attach at most 8 photos. Keeping the first ${room}.`);
  }
  for (const f of files.slice(0, room)) {
    try {
      gradeImages.push(await resizeImage(f));
    } catch (err) {
      console.error("Failed to process", f.name, err);
      alert(`Couldn't read ${f.name || "image"} — is it a valid image?`);
    }
  }
  renderImagePreviews();
}

gradeImagesInput.addEventListener("change", async (e) => {
  await ingestFiles(e.target.files);
  gradeImagesInput.value = ""; // allow re-selecting the same file
});

// ---------- Drag & drop + click-to-browse + paste ----------
const gradeDropzone = document.getElementById("grade-dropzone");

gradeDropzone.addEventListener("click", (e) => {
  // Don't re-trigger if the click came from the hidden input itself or a child control
  if (e.target === gradeImagesInput) return;
  gradeImagesInput.click();
});

["dragenter", "dragover"].forEach((ev) =>
  gradeDropzone.addEventListener(ev, (e) => {
    e.preventDefault();
    e.stopPropagation();
    gradeDropzone.classList.add("border-blue-400", "bg-gray-800");
  })
);

["dragleave", "drop"].forEach((ev) =>
  gradeDropzone.addEventListener(ev, (e) => {
    e.preventDefault();
    e.stopPropagation();
    gradeDropzone.classList.remove("border-blue-400", "bg-gray-800");
  })
);

gradeDropzone.addEventListener("drop", async (e) => {
  await ingestFiles(e.dataTransfer?.files);
});

// Paste an image from clipboard (Ctrl/Cmd+V) anywhere on the grader tab.
// Only fires when the grader tab is visible and the paste contains an image.
document.addEventListener("paste", async (e) => {
  const graderVisible = !document.getElementById("tab-grader").classList.contains("hidden");
  if (!graderVisible) return;
  const items = Array.from(e.clipboardData?.items || []);
  const imageFiles = items
    .filter((it) => it.kind === "file" && it.type.startsWith("image/"))
    .map((it) => it.getAsFile())
    .filter(Boolean);
  if (imageFiles.length) {
    e.preventDefault();
    await ingestFiles(imageFiles);
  }
});

gradeForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const problem = document.getElementById("grade-problem").value.trim();
  const work = document.getElementById("grade-work").value.trim();
  if (!problem) return;
  if (!work && gradeImages.length === 0) {
    alert("Add some typed working, upload photos of handwritten work, or both.");
    return;
  }
  gradeOut.innerHTML = '<div class="text-gray-400 text-sm">Reading your work carefully…</div>';
  try {
    const payload = {
      problem,
      student_work: work,
      images: gradeImages.map(({ media_type, data }) => ({ media_type, data })),
    };
    const r = await apiFetch(API + "/api/grade", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    const g = await r.json();
    const verdictColor = { correct: "text-green-400", partially_correct: "text-amber-400", incorrect: "text-red-400" }[g.verdict] || "text-gray-300";
    gradeOut.innerHTML = `
      <div class="bg-gray-800 rounded-lg p-4 space-y-3">
        <div class="flex items-center gap-4">
          <div class="${verdictColor} font-semibold uppercase text-sm">${g.verdict.replace("_", " ")}</div>
          <div class="text-sm text-gray-400">Score: ${g.score_out_of_10}/10</div>
          <div class="text-sm text-gray-400">Error type: ${g.error_type.replace("_", " ")}</div>
        </div>
        ${g.what_was_right ? `<div><div class="text-xs text-green-300 mb-1">What you got right</div><div class="prose-cap">${renderMarkdown(g.what_was_right)}</div></div>` : ""}
        ${g.first_error_step ? `<div><div class="text-xs text-amber-300 mb-1">Where things went off</div><div class="prose-cap">${renderMarkdown(g.first_error_step)}</div></div>` : ""}
        <div><div class="text-xs text-blue-300 mb-1">Feedback</div><div class="prose-cap">${renderMarkdown(g.feedback)}</div></div>
        <div class="pt-3 border-t border-gray-700">
          <div class="text-xs text-gray-400 mb-1">Next step</div>
          <div class="prose-cap text-sm">${renderMarkdown(g.suggested_next_step)}</div>
        </div>
      </div>
    `;
    typeset(gradeOut);
  } catch (err) {
    gradeOut.innerHTML = `<div class="text-red-400">Error: ${err.message}</div>`;
  }
});

// ---------- Flashcards ----------
const cardsForm = document.getElementById("cards-form");
const cardsOut = document.getElementById("cards-out");

cardsForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const topic = document.getElementById("cards-topic").value;
  cardsOut.innerHTML = '<div class="text-gray-400 text-sm col-span-full">Building deck…</div>';
  try {
    const r = await apiFetch(API + "/api/flashcards", {
      method: "POST",
      body: JSON.stringify({ topic, count: 10 }),
    });
    const deck = await r.json();
    if (!Array.isArray(deck.cards) || deck.cards.length === 0) {
      cardsOut.innerHTML = `<div class="text-red-400 col-span-full">No cards returned. Try again?</div>`;
      return;
    }
    cardsOut.innerHTML = deck.cards
      .map((c, i) => {
        const badge = { definition: "bg-blue-900", equation: "bg-purple-900", concept: "bg-green-900", pitfall: "bg-red-900" }[c.category] || "bg-gray-700";
        return `
          <div class="flip-card h-52" data-idx="${i}">
            <div class="flip-card-inner">
              <div class="flip-card-front bg-gray-800 flex flex-col">
                <div class="flex items-center justify-between w-full text-xs mb-2">
                  <span class="px-2 py-0.5 rounded ${badge}">${c.category}</span>
                  <span class="text-gray-500">difficulty ${c.difficulty}</span>
                </div>
                <div class="flex-1 flex items-center justify-center prose-cap text-center">${renderMarkdown(c.front)}</div>
                <div class="text-xs text-gray-500 mt-auto">Click to flip</div>
              </div>
              <div class="flip-card-back bg-gray-700 prose-cap text-sm text-left overflow-auto">${renderMarkdown(c.back)}</div>
            </div>
          </div>
        `;
      })
      .join("");
    cardsOut.querySelectorAll(".flip-card").forEach((el) => {
      el.addEventListener("click", () => el.classList.toggle("flipped"));
    });
    typeset(cardsOut);
  } catch (err) {
    cardsOut.innerHTML = `<div class="text-red-400 col-span-full">Error: ${err.message}</div>`;
  }
});

// ---------- Welcome message ----------
addBubble(
  "assistant",
  "Welcome aboard! I'm Captain Thermo. I'll help you work through MS1016 problems — but I'll steer you through the reasoning, not just give answers. What are you working on?"
);
