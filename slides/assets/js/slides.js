/* =============================================================================
   Minimal slide runner. No dependencies, no build step.

   Keys:  → ← space   navigate        N  speaker notes
          O           overview        T  session timer
          A           agenda          F  fullscreen
          Home / End  first / last    P  print (export PDF)
          ?           help

   Mouse: click anywhere to advance. Move the mouse to wake the on-screen
          controls in the bottom-right corner; they fade again when you stop.
   Touch: swipe left / right.
   ========================================================================== */

(function () {
  "use strict";

  const slides = Array.from(document.querySelectorAll(".slide"));
  const progress = document.getElementById("progress");
  const ticks = document.getElementById("ticks");
  const counter = document.getElementById("counter");
  const notesEl = document.getElementById("notes");
  const timerEl = document.getElementById("timer");
  const overviewEl = document.getElementById("overview");
  const helpEl = document.getElementById("help");
  const controls = document.getElementById("controls");
  const secLabel = document.getElementById("seclabel");
  const btnPrev = document.getElementById("btn-prev");
  const btnNext = document.getElementById("btn-next");

  const TALK_MINUTES = 90;
  let index = 0;
  let timerStart = null;

  // --- Sections -------------------------------------------------------------
  // Derived from the divider slides rather than hardcoded, so inserting a slide
  // never desynchronises the agenda or the progress ticks.
  const dividers = slides
    .map((slide, i) => (slide.classList.contains("divider") ? i : -1))
    .filter((i) => i >= 0);

  const sectionStarts = [0].concat(dividers);

  const sectionNames = sectionStarts.map((start, i) => {
    if (i === 0) return "Intro";
    const heading = slides[start].querySelector("h1");
    return heading ? heading.textContent.trim() : "Section " + i;
  });

  function sectionOf(i) {
    let s = 0;
    for (let k = 0; k < sectionStarts.length; k++) {
      if (i >= sectionStarts[k]) s = k;
    }
    return s;
  }

  // The slide you were on before jumping to the agenda, so the agenda can show
  // you where you came from when you use it mid-talk.
  const agendaIndex = slides.findIndex((slide) => slide.id === "agenda");
  let lastNonAgenda = 0;

  // --- Scale the fixed 1280x720 stage to fit the window ---------------------
  function fit() {
    const scale = Math.min(
      window.innerWidth / 1280,
      window.innerHeight / 720
    );
    document.documentElement.style.setProperty("--scale", scale.toFixed(4));
  }

  // --- Navigation ------------------------------------------------------------
  function show(next, { push = true } = {}) {
    index = Math.max(0, Math.min(slides.length - 1, next));
    if (index !== agendaIndex) lastNonAgenda = index;

    slides.forEach((slide, i) => slide.classList.toggle("current", i === index));

    progress.style.width = ((index + 1) / slides.length) * 100 + "%";
    counter.textContent = `${index + 1} / ${slides.length}`;
    secLabel.textContent = sectionNames[sectionOf(index)];

    btnPrev.disabled = index === 0;
    btnNext.disabled = index === slides.length - 1;

    renderNotes();
    if (index === agendaIndex) markAgenda();

    document
      .querySelectorAll(".thumb")
      .forEach((t, i) => t.classList.toggle("current", i === index));

    if (push) history.replaceState(null, "", "#" + (index + 1));
  }

  const next = () => show(index + 1);
  const prev = () => show(index - 1);

  function goToId(id) {
    const target = slides.findIndex((slide) => slide.id === id);
    if (target >= 0) show(target);
  }

  const goAgenda = () => (agendaIndex >= 0 ? show(agendaIndex) : show(0));

  // --- Agenda ----------------------------------------------------------------
  const agendaRows = Array.from(document.querySelectorAll(".ag-row"));

  agendaRows.forEach((row) =>
    row.addEventListener("click", () => goToId(row.dataset.goto))
  );

  /** Mark the row for the block you were last in. */
  function markAgenda() {
    const here = sectionOf(lastNonAgenda);
    agendaRows.forEach((row) => {
      const target = slides.findIndex((slide) => slide.id === row.dataset.goto);
      row.classList.toggle("here", target >= 0 && sectionOf(target) === here);
    });
  }

  // --- Speaker notes ---------------------------------------------------------
  function renderNotes() {
    const source = slides[index].querySelector(".notes");
    notesEl.innerHTML =
      "<h4>Speaker notes — slide " +
      (index + 1) +
      "</h4>" +
      (source ? source.innerHTML : "<p class='small'>—</p>");
  }

  // --- Session timer ---------------------------------------------------------
  function tickTimer() {
    if (timerStart === null) return;
    const seconds = Math.floor((Date.now() - timerStart) / 1000);
    const mm = String(Math.floor(seconds / 60)).padStart(2, "0");
    const ss = String(seconds % 60).padStart(2, "0");

    // Where you *should* be, if you paced the deck evenly.
    const expected = Math.round(((index + 1) / slides.length) * TALK_MINUTES);
    timerEl.textContent = `${mm}:${ss}  ·  on-pace ${expected}m`;
    timerEl.classList.toggle("over", seconds / 60 > TALK_MINUTES);
  }
  setInterval(tickTimer, 1000);

  // --- Overview --------------------------------------------------------------
  function buildOverview() {
    overviewEl.innerHTML = slides
      .map((slide, i) => {
        const heading = slide.querySelector("h1, h2");
        const title =
          slide.dataset.title ||
          (heading ? heading.textContent.trim() : "—");
        return `<div class="thumb" data-goto="${i}">
                  <div class="n">${String(i + 1).padStart(2, "0")}</div>
                  <div class="t">${title}</div>
                </div>`;
      })
      .join("");

    overviewEl.querySelectorAll(".thumb").forEach((thumb) =>
      thumb.addEventListener("click", () => {
        show(Number(thumb.dataset.goto));
        overviewEl.classList.add("hidden");
      })
    );
  }

  /** Small marks on the progress bar showing where each section begins. */
  function buildTicks() {
    ticks.innerHTML = dividers
      .map((d) => `<i style="left:${(d / slides.length) * 100}%"></i>`)
      .join("");
  }

  const toggle = (el) => el.classList.toggle("hidden");

  // --- On-screen controls ----------------------------------------------------
  // Faint at rest so they never compete with what's projected.
  let wakeTimer = null;
  function wake() {
    controls.classList.add("awake");
    clearTimeout(wakeTimer);
    wakeTimer = setTimeout(() => controls.classList.remove("awake"), 2600);
  }
  // Mouse only: when you're driving from the keyboard or a clicker, the
  // projected image stays clean.
  document.addEventListener("mousemove", wake);

  btnPrev.addEventListener("click", prev);
  btnNext.addEventListener("click", next);
  document.getElementById("btn-agenda").addEventListener("click", goAgenda);
  document.getElementById("btn-overview").addEventListener("click", () => toggle(overviewEl));
  document.getElementById("btn-notes").addEventListener("click", () => toggle(notesEl));

  // --- Keyboard --------------------------------------------------------------
  document.addEventListener("keydown", (event) => {
    if (event.metaKey || event.ctrlKey || event.altKey) return;

    switch (event.key) {
      case "ArrowRight":
      case "PageDown":
      case " ":
      case "Enter":
        event.preventDefault();
        next();
        break;
      case "ArrowLeft":
      case "PageUp":
        event.preventDefault();
        prev();
        break;
      case "Home": show(0); break;
      case "End": show(slides.length - 1); break;
      case "a": case "A": goAgenda(); break;
      case "n": case "N": toggle(notesEl); break;
      case "o": case "O": toggle(overviewEl); break;
      case "f": case "F":
        if (document.fullscreenElement) document.exitFullscreen();
        else document.documentElement.requestFullscreen();
        break;
      case "t": case "T":
        if (timerStart === null) {
          timerStart = Date.now();
          timerEl.classList.remove("hidden");
        } else {
          timerStart = null;
          timerEl.classList.add("hidden");
        }
        break;
      case "p": case "P": window.print(); break;
      case "?": toggle(helpEl); break;
      case "Escape":
        overviewEl.classList.add("hidden");
        helpEl.classList.add("hidden");
        break;
    }
  });

  // --- Touch -----------------------------------------------------------------
  let touchX = 0;
  let touchY = 0;
  let swiped = false;

  document.addEventListener(
    "touchstart",
    (event) => {
      touchX = event.changedTouches[0].clientX;
      touchY = event.changedTouches[0].clientY;
    },
    { passive: true }
  );

  document.addEventListener(
    "touchend",
    (event) => {
      const dx = event.changedTouches[0].clientX - touchX;
      const dy = event.changedTouches[0].clientY - touchY;
      // Horizontal, and clearly more horizontal than vertical, so scrolling the
      // notes panel on a phone doesn't change slide.
      if (Math.abs(dx) > 55 && Math.abs(dx) > Math.abs(dy) * 1.5) {
        swiped = true;
        if (dx < 0) next();
        else prev();
      }
    },
    { passive: true }
  );

  // Click / tap to advance — but not on links, buttons, or any panel.
  document.addEventListener("click", (event) => {
    // A swipe also fires a click; ignore that one so it doesn't undo the swipe.
    if (swiped) {
      swiped = false;
      return;
    }
    if (event.target.closest("a, button, #controls, #notes, #overview, #help")) return;
    next();
  });

  // --- Boot ------------------------------------------------------------------
  window.addEventListener("resize", fit);
  fit();
  buildOverview();
  buildTicks();

  const fromHash = parseInt(location.hash.replace("#", ""), 10);
  show(Number.isFinite(fromHash) && fromHash > 0 ? fromHash - 1 : 0);

  notesEl.classList.add("hidden");
  timerEl.classList.add("hidden");
  helpEl.classList.add("hidden");
  overviewEl.classList.add("hidden");
})();
