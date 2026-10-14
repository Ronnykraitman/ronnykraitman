/* Ronny Kraitman · AI chat client */
(() => {
  "use strict";

  const $ = (sel) => document.querySelector(sel);
  const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ───────────── Circuit pulses on top of the background art ───────────── */
  function startCircuit() {
    const canvas = $("#circuit");
    const ctx = canvas.getContext("2d");
    const GRID = 44;
    let w = 0, h = 0, dpr = 1, pulses = [];

    const resize = () => {
      dpr = Math.min(devicePixelRatio || 1, 2);
      w = canvas.clientWidth; h = canvas.clientHeight;
      canvas.width = w * dpr; canvas.height = h * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    const DIRS = [[1, 0], [-1, 0], [0, 1], [0, -1]];
    const spawn = () => {
      // bias pulses to the right side where the circuitry lives in the artwork
      const minX = w < 960 ? 0 : w * 0.42;
      const x = Math.round((minX + Math.random() * (w - minX)) / GRID) * GRID;
      const y = Math.round((Math.random() * h) / GRID) * GRID;
      const [dx, dy] = DIRS[(Math.random() * 4) | 0];
      return {
        pts: [[x, y]], x, y, dx, dy,
        speed: 1.2 + Math.random() * 1.8,
        life: 220 + Math.random() * 260,
        hue: Math.random() < 0.75 ? 192 : 250,
      };
    };
    const COUNT = () => (w < 960 ? 6 : 14);

    const tick = () => {
      ctx.clearRect(0, 0, w, h);
      while (pulses.length < COUNT()) pulses.push(spawn());
      pulses = pulses.filter((p) => p.life > 0 && p.x > -GRID && p.x < w + GRID && p.y > -GRID && p.y < h + GRID);

      for (const p of pulses) {
        p.x += p.dx * p.speed; p.y += p.dy * p.speed; p.life -= 1;
        const onNode = Math.abs(p.x % GRID) < p.speed && Math.abs(p.y % GRID) < p.speed;
        if (onNode && Math.random() < 0.22) {
          p.pts.push([p.x, p.y]);
          [p.dx, p.dy] = p.dx ? [0, Math.random() < 0.5 ? 1 : -1] : [Math.random() < 0.5 ? 1 : -1, 0];
        }
        const fade = Math.min(1, p.life / 60);
        const path = [...p.pts.slice(-4), [p.x, p.y]];
        ctx.lineWidth = 1.4;
        ctx.strokeStyle = `hsla(${p.hue}, 100%, 65%, ${0.35 * fade})`;
        ctx.shadowColor = `hsla(${p.hue}, 100%, 60%, ${fade})`;
        ctx.shadowBlur = 10;
        ctx.beginPath();
        path.forEach(([px, py], i) => (i ? ctx.lineTo(px, py) : ctx.moveTo(px, py)));
        ctx.stroke();
        ctx.fillStyle = `hsla(${p.hue}, 100%, 80%, ${fade})`;
        ctx.beginPath(); ctx.arc(p.x, p.y, 1.8, 0, Math.PI * 2); ctx.fill();
        if (p.pts.length > 6) p.pts.shift();
      }
      ctx.shadowBlur = 0;
      raf = requestAnimationFrame(tick);
    };

    let raf = 0;
    resize();
    addEventListener("resize", resize);
    document.addEventListener("visibilitychange", () => {
      cancelAnimationFrame(raf);
      if (!document.hidden) raf = requestAnimationFrame(tick);
    });
    raf = requestAnimationFrame(tick);
  }

  /* ───────────── Typed role line ───────────── */
  function startTyping() {
    const el = $("#typed");
    const lines = [
      "Senior AI & Backend Engineer",
      "LLM agents · RAG · production AI",
      "distributed data · Kafka · Airflow",
      "ML from whiteboard to 20ms serving",
    ];
    let li = 0, ci = lines[0].length, deleting = true;
    const step = () => {
      const line = lines[li];
      if (deleting) {
        ci--;
        if (ci <= 0) { deleting = false; li = (li + 1) % lines.length; }
      } else {
        ci++;
        if (ci >= lines[li].length) { deleting = true; el.textContent = lines[li]; return setTimeout(step, 2600); }
      }
      el.textContent = (deleting ? line : lines[li]).slice(0, ci);
      setTimeout(step, deleting ? 28 : 55);
    };
    setTimeout(step, 3200);
  }

  /* ───────────── Chat ───────────── */
  const STORE_KEY = "rk.chat.v1";
  const USER_AVATAR_KEY = "rk.avatar";
  const BOT_AVATAR = "/media/ronnyk_avatar.jpg";
  const GREETING =
    "Hey, I'm **Ronny** — well, my AI twin 🤖. I build backend systems and bring **LLMs and ML to production**.\n\n" +
    "Ask me about architecture, data pipelines, AI agents, or the time I got an ML model serving in `20ms`. What's your name?";
  const THINKING_STEPS = ["parsing intent", "retrieving resume context", "reasoning over experience", "composing answer"];

  const els = {
    console: $(".console"),
    list: $("#messages"),
    form: $("#composer"),
    input: $("#input"),
    send: $("#sendBtn"),
    reset: $("#resetBtn"),
    suggestions: $("#suggestions"),
    session: $("#sessionId"),
    last: $("#lastLatency"),
    model: $("#modelLabel"),
    resumeTpl: $("#tpl-resume-card"),
  };

  const userAvatar =
    sessionStorage.getItem(USER_AVATAR_KEY) ||
    (() => {
      const a = `/media/avatar_${1 + ((Math.random() * 9) | 0)}.png`;
      sessionStorage.setItem(USER_AVATAR_KEY, a);
      return a;
    })();

  let state = load();
  let controller = null;

  function newState() {
    return {
      session: crypto.getRandomValues(new Uint32Array(1))[0].toString(16).padStart(8, "0"),
      messages: [{ role: "assistant", content: GREETING, local: true }],
    };
  }
  function load() {
    try {
      const s = JSON.parse(sessionStorage.getItem(STORE_KEY));
      if (s && Array.isArray(s.messages)) return s;
    } catch { /* ignore */ }
    return newState();
  }
  const save = () => sessionStorage.setItem(STORE_KEY, JSON.stringify(state));

  /* Markdown (marked + DOMPurify + highlight.js) */
  let mdReady = false;
  function setupMarkdown() {
    if (mdReady || !window.marked || !window.DOMPurify) return mdReady;
    marked.setOptions({ gfm: true, breaks: true });
    DOMPurify.addHook("afterSanitizeAttributes", (node) => {
      if (node.tagName === "A") { node.setAttribute("target", "_blank"); node.setAttribute("rel", "noopener noreferrer"); }
    });
    return (mdReady = true);
  }
  function renderInto(el, text, final) {
    if (setupMarkdown()) {
      el.innerHTML = DOMPurify.sanitize(marked.parse(text));
      if (final && window.hljs) el.querySelectorAll("pre code").forEach((c) => hljs.highlightElement(c));
    } else {
      el.textContent = text;
    }
  }

  const nearBottom = () => els.list.scrollHeight - els.list.scrollTop - els.list.clientHeight < 120;
  const scrollDown = (force) => { if (force || nearBottom()) els.list.scrollTop = els.list.scrollHeight; };

  function metaHTML(meta) {
    if (!meta) return "";
    const s = (meta.latency_ms / 1000).toFixed(2);
    const tok = Math.max(1, Math.round(meta.chars / 4));
    return `<span>⏱ <b>${s}s</b></span><span>ttft <b>${meta.ttft_ms}ms</b></span><span>~<b>${tok}</b> tokens</span>`;
  }

  function buildMessage(msg) {
    const isUser = msg.role === "user";
    const wrap = document.createElement("article");
    wrap.className = `msg ${isUser ? "msg--user" : "msg--bot"}${msg.error ? " msg--error" : ""}`;

    const img = document.createElement("img");
    img.className = "msg__avatar";
    img.alt = isUser ? "You" : "Ronny";
    img.src = isUser ? userAvatar : BOT_AVATAR;

    const col = document.createElement("div");
    col.className = "msg__col";
    const body = document.createElement("div");
    body.className = "msg__body";
    if (isUser) body.textContent = msg.content;
    else renderInto(body, msg.content, true);
    col.append(body);

    if (msg.tool === "resume") col.append(els.resumeTpl.content.cloneNode(true));
    if (msg.meta) {
      const meta = document.createElement("div");
      meta.className = "msg__meta";
      meta.innerHTML = metaHTML(msg.meta);
      col.append(meta);
    }
    wrap.append(img, col);
    return { wrap, col, body };
  }

  function renderAll() {
    els.list.replaceChildren(...state.messages.map((m) => buildMessage(m).wrap));
    els.session.textContent = state.session;
    els.suggestions.hidden = state.messages.some((m) => m.role === "user");
    scrollDown(true);
  }

  function setStreaming(on) {
    els.console.classList.toggle("is-streaming", on);
    els.list.setAttribute("aria-busy", String(on));
    els.send.setAttribute("aria-label", on ? "Stop generating" : "Send");
    updateSendState();
  }
  const updateSendState = () => { els.send.disabled = !controller && !els.input.value.trim(); };

  async function send(text) {
    text = text.trim();
    if (!text || controller) return;

    state.messages.push({ role: "user", content: text });
    save();
    els.list.append(buildMessage({ role: "user", content: text }).wrap);
    els.suggestions.hidden = true;
    els.input.value = "";
    autoGrow();
    scrollDown(true);

    // Bot placeholder with a live "agent trace"
    const bot = { role: "assistant", content: "" };
    const { wrap, col, body } = buildMessage(bot);
    body.remove();
    const trace = document.createElement("div");
    trace.className = "thinking";
    col.append(trace);
    els.list.append(wrap);

    let stepIdx = 0;
    const pushStep = () => {
      trace.querySelector(".is-active")?.classList.remove("is-active");
      const s = document.createElement("div");
      s.className = "thinking__step is-active";
      s.textContent = THINKING_STEPS[stepIdx] + "…";
      trace.append(s);
      scrollDown();
    };
    pushStep();
    const stepTimer = setInterval(() => {
      if (stepIdx < THINKING_STEPS.length - 1) { stepIdx++; pushStep(); }
    }, 750);

    let started = false;
    let frame = 0;
    const startBody = () => {
      if (started) return;
      started = true;
      clearInterval(stepTimer);
      trace.remove();
      body.classList.add("cursor");
      col.prepend(body);
    };
    const paint = () => {
      frame = 0;
      renderInto(body, bot.content, false);
      scrollDown();
    };

    controller = new AbortController();
    setStreaming(true);

    try {
      const history = state.messages.filter((m) => !m.local && !m.error).map(({ role, content }) => ({ role, content }));
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: history }),
        signal: controller.signal,
      });
      if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);

      const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
      let buf = "";
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += value;
        let idx;
        while ((idx = buf.indexOf("\n\n")) !== -1) {
          const raw = buf.slice(0, idx);
          buf = buf.slice(idx + 2);
          const line = raw.split("\n").find((l) => l.startsWith("data:"));
          if (!line) continue;
          const ev = JSON.parse(line.slice(5));
          if (ev.type === "delta") {
            startBody();
            bot.content += ev.text;
            if (!frame) frame = requestAnimationFrame(paint);
          } else if (ev.type === "tool" && ev.name === "offer_resume_download") {
            bot.tool = "resume";
          } else if (ev.type === "error") {
            bot.error = !bot.content;
            bot.content += (bot.content ? "\n\n" : "") + `⚠️ ${ev.message}`;
          } else if (ev.type === "done") {
            bot.meta = ev;
          }
        }
      }
    } catch (err) {
      if (err.name !== "AbortError") {
        bot.error = !bot.content;
        bot.content += (bot.content ? "\n\n" : "") + "⚠️ Connection dropped somewhere between my neurons and your browser. Try again?";
      }
    } finally {
      clearInterval(stepTimer);
      cancelAnimationFrame(frame);
      controller = null;
      setStreaming(false);

      if (!bot.content && bot.tool === "resume") bot.content = "Here you go — fresh off the build pipeline 👇";
      if (!bot.content) bot.content = "_(stopped)_";
      state.messages.push(bot);
      save();
      wrap.replaceWith(buildMessage(bot).wrap);
      if (bot.meta) els.last.textContent = `${(bot.meta.latency_ms / 1000).toFixed(2)}s`;
      scrollDown(true);
      els.input.focus({ preventScroll: true });
    }
  }

  /* Composer: field-sizing: content auto-grows; small fallback for older browsers */
  const supportsFieldSizing = CSS.supports("field-sizing", "content");
  function autoGrow() {
    if (supportsFieldSizing) return;
    const ta = els.input;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 160) + "px";
  }

  els.input.addEventListener("input", () => { autoGrow(); updateSendState(); });
  els.input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
      e.preventDefault();
      els.form.requestSubmit();
    }
  });
  els.form.addEventListener("submit", (e) => {
    e.preventDefault();
    if (controller) controller.abort();
    else send(els.input.value);
  });
  els.suggestions.addEventListener("click", (e) => {
    const b = e.target.closest("button[data-q]");
    if (b) send(b.dataset.q);
  });
  els.reset.addEventListener("click", () => {
    controller?.abort();
    state = newState();
    save();
    renderAll();
    els.last.textContent = "—";
    els.input.focus();
  });

  fetch("/api/health")
    .then((r) => r.json())
    .then((h) => { if (h.model) els.model.textContent = `online · ${h.model}`; })
    .catch(() => { els.model.textContent = "offline"; });

  // Libraries are deferred; re-render once they're available so markdown is pretty.
  addEventListener("DOMContentLoaded", () => {
    renderAll();
    updateSendState();
    if (!reduceMotion) { startCircuit(); startTyping(); }
    if (matchMedia("(pointer: fine)").matches) els.input.focus({ preventScroll: true });
  });
})();
