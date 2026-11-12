/* Shared frontend helpers: API access, language, reveal, tilt, formatting.

   Vanilla ES modules, no build step. Every page imports from here so the
   behaviour stays identical across the five surfaces. */

const LANG_KEY = "ve.lang";
const SESSION_KEY = "ve.session";

export const LANGS = [
  { code: "en-IN", label: "English", native: "English", script: "Latin" },
  { code: "hi-IN", label: "Hindi", native: "हिन्दी", script: "Devanagari" },
  { code: "bn-IN", label: "Bengali", native: "বাংলা", script: "Bengali" },
  { code: "ta-IN", label: "Tamil", native: "தமிழ்", script: "Tamil" },
  { code: "te-IN", label: "Telugu", native: "తెలుగు", script: "Telugu" },
];

export function lang() {
  return localStorage.getItem(LANG_KEY) || "en-IN";
}

export function setLang(code) {
  localStorage.setItem(LANG_KEY, code);
  document.documentElement.lang = code;
}

function sessionId() {
  let id = localStorage.getItem(SESSION_KEY);
  if (!id) {
    id = "web-" + Math.random().toString(16).slice(2, 10);
    localStorage.setItem(SESSION_KEY, id);
  }
  return id;
}

/** fetch wrapper: JSON in, JSON out, one error shape.
 *
 *  ``window.VE_API`` is the API origin. Empty means same origin (local uvicorn
 *  or a single-process Render deploy). When the static front end is hosted
 *  separately — Netlify, for instance — set the <meta name="ve-api"> tag to the
 *  backend URL and every call follows it.
 */
export async function api(path, options = {}) {
  const response = await fetch((window.VE_API || "") + path, {
    headers: {
      "Content-Type": "application/json",
      "X-Session-Id": sessionId(),
    },
    ...options,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`${response.status}: ${text.slice(0, 200)}`);
  }
  return response.json();
}

/* -------------------------------------------------------------- rendering */

export const $ = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

export function esc(text) {
  return String(text ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[char]);
}

export function chip(label, kind = "") {
  return `<span class="chip ${kind}">${esc(label)}</span>`;
}

export function toast(message) {
  let node = $(".toast");
  if (!node) {
    node = document.createElement("div");
    node.className = "toast";
    document.body.appendChild(node);
  }
  node.textContent = message;
  node.classList.add("show");
  clearTimeout(node._timer);
  node._timer = setTimeout(() => node.classList.remove("show"), 2600);
}

/* ------------------------------------------------------------------ chrome */

export function mountChrome(active) {
  const select = $("#lang-select");
  if (select) {
    select.innerHTML = LANGS.map(
      (item) => `<option value="${item.code}">${item.native}</option>`
    ).join("");
    select.value = lang();
    select.addEventListener("change", (event) => {
      setLang(event.target.value);
      location.reload();
    });
  }
  $$(".nav a").forEach((link) => {
    if (link.getAttribute("href") === active) link.setAttribute("aria-current", "page");
  });
  document.documentElement.lang = lang();
}

/** Fill every [data-i18n] node from the server's string table. */
export async function applyStrings() {
  try {
    const strings = await api(`/api/ui-strings?lang=${lang()}`);
    $$("[data-i18n]").forEach((node) => {
      const key = node.dataset.i18n;
      if (strings[key]) node.textContent = strings[key];
    });
    $$("[data-i18n-ph]").forEach((node) => {
      const key = node.dataset.i18nPh;
      if (strings[key]) node.placeholder = strings[key];
    });
    return strings;
  } catch (error) {
    console.warn("i18n unavailable", error);
    return {};
  }
}

export async function health() {
  try {
    return await api("/api/health");
  } catch {
    return { mode: "offline", events: 0 };
  }
}

/* ------------------------------------------------------------------ motion */

export function reveal(root = document) {
  const nodes = $$(".reveal", root);
  if (!("IntersectionObserver" in window)) {
    nodes.forEach((node) => node.classList.add("in"));
    return;
  }
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("in");
          observer.unobserve(entry.target);
        }
      });
    },
    { rootMargin: "0px 0px -8% 0px", threshold: 0.08 }
  );
  nodes.forEach((node, index) => {
    node.style.transitionDelay = `${Math.min(index % 6, 5) * 60}ms`;
    observer.observe(node);
  });
}

/** Pointer-tracked 3D tilt + sheen on any [data-tilt] element. */
export function tilt(root = document) {
  $$("[data-tilt]", root).forEach((card) => {
    if (card.dataset.tiltBound) return;
    card.dataset.tiltBound = "1";
    const MAX = 7;
    card.addEventListener("pointermove", (event) => {
      const box = card.getBoundingClientRect();
      const px = (event.clientX - box.left) / box.width;
      const py = (event.clientY - box.top) / box.height;
      card.style.setProperty("--ty", `${(px - 0.5) * 2 * MAX}deg`);
      card.style.setProperty("--tx", `${(0.5 - py) * 2 * MAX}deg`);
      card.style.setProperty("--mx", `${px * 100}%`);
      card.style.setProperty("--my", `${py * 100}%`);
    });
    card.addEventListener("pointerleave", () => {
      card.style.setProperty("--tx", "0deg");
      card.style.setProperty("--ty", "0deg");
    });
  });
}

/** Count a number up when it scrolls into view. */
export function countUp(root = document) {
  $$("[data-count]", root).forEach((node) => {
    const target = Number(node.dataset.count || 0);
    if (!target) {
      node.textContent = "0";
      return;
    }
    const observer = new IntersectionObserver((entries) => {
      if (!entries[0].isIntersecting) return;
      observer.disconnect();
      const started = performance.now();
      const tick = (now) => {
        const progress = Math.min((now - started) / 900, 1);
        node.textContent = String(Math.round(target * (1 - Math.pow(1 - progress, 3))));
        if (progress < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    });
    observer.observe(node);
  });
}

/** Slow parallax drift on the background blobs. */
export function parallax() {
  const blobs = $$(".blob");
  if (!blobs.length || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const state = { x: 0, y: 0, tx: 0, ty: 0 };
  window.addEventListener(
    "pointermove",
    (event) => {
      state.tx = event.clientX / innerWidth - 0.5;
      state.ty = event.clientY / innerHeight - 0.5;
    },
    { passive: true }
  );
  const loop = () => {
    state.x += (state.tx - state.x) * 0.045;
    state.y += (state.ty - state.y) * 0.045;
    blobs.forEach((blob, index) => {
      const depth = (index + 1) * 9;
      blob.style.translate = `${(state.x * depth).toFixed(1)}px ${(state.y * depth).toFixed(1)}px`;
    });
    requestAnimationFrame(loop);
  };
  loop();
}

export function boot(active) {
  document.body.classList.remove("no-js");
  mountChrome(active);
  reveal();
  tilt();
  countUp();
  parallax();
  return applyStrings();
}
