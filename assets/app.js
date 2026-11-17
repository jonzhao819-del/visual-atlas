/* =========================================================
   视觉风格参考档案 · app.js
   纯原生 JS，无依赖；数据来自 assets/data.js
   ========================================================= */
(function () {
  "use strict";

  const DATA = Array.isArray(window.ATLAS_DATA) ? window.ATLAS_DATA : [];
  const META = window.ATLAS_META || {};
  const CHAPTERS = META.chapters || [];
  const CHAP = new Map(CHAPTERS.map((c) => [c.chapter, c]));

  const KIND_LABEL = { historical: "历史技法", digital: "数字管线", custom: "自建" };
  const BODY_LABEL = {
    "Identify": "识别",
    "Principle": "原理",
    "Try it out": "怎么试",
    "Example": "例子",
    "Classification": "归类"
  };
  const BODY_EN = {
    "Identify": "Identify",
    "Principle": "Principle",
    "Try it out": "Try it out",
    "Example": "Example",
    "Classification": "Classification"
  };

  const $ = (sel, root) => (root || document).querySelector(sel);
  const $$ = (sel, root) => Array.prototype.slice.call((root || document).querySelectorAll(sel));
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const norm = (s) => String(s == null ? "" : s).normalize("NFKD").replace(/[\u0300-\u036f]/g, "").toLowerCase();

  const BATCH = 72;
  const FAV_KEY = "vsa:favorites:v1";

  // 对话里的文档预览是 blob iframe（sandbox 只允许脚本），读不到本地图片
  const IN_PREVIEW =
    location.protocol === "blob:" ||
    location.protocol === "about:" ||
    location.protocol === "data:" ||
    (window.self !== window.top && location.protocol === "file:");
  let imgFails = 0;
  let noteShown = false;

  const state = {
    kind: "all",
    decade: "",
    chapter: "",
    sort: "plate",
    q: "",
    shown: BATCH
  };

  let view = [];          // 当前筛选结果
  let currentSlug = null; // 详情打开中的条目

  /* ---------------- 收藏 ---------------- */
  function readFavs() {
    try {
      const raw = localStorage.getItem(FAV_KEY);
      const arr = raw ? JSON.parse(raw) : [];
      return new Set(Array.isArray(arr) ? arr : []);
    } catch (e) {
      return new Set();
    }
  }
  function writeFavs(set) {
    try { localStorage.setItem(FAV_KEY, JSON.stringify(Array.from(set))); } catch (e) { /* 隐私模式忽略 */ }
  }
  let favs = readFavs();

  /* ---------------- 工具 ---------------- */
  function chapterOf(e) {
    return CHAP.get(e.chapter) || null;
  }
  function yearOf(e) {
    const d = String(e.decade || "").match(/(\d{4})/);
    if (d) return Number(d[1]);
    const t = String(e.dating || "").match(/\b(1[5-9]\d{2}|20\d{2})\b/);
    return t ? Number(t[1]) : null;
  }
  function searchBlob(e) {
    if (!e.__blob) {
      const ch = chapterOf(e);
      e.__blob = norm([
        e.title, e.titleZh, e.name, e.slug, e.short, e.decade, e.dating, e.prompt, e.credit,
        (e.body || []).map((b) => b.text).join(" "),
        (e.highlights || []).join(" "),
        ch ? ch.en + " " + ch.zh : "",
        KIND_LABEL[e.kind] || ""
      ].join(" "));
    }
    return e.__blob;
  }

  const byPlate = (a, b) => (a.plate || 0) - (b.plate || 0);

  function showPreviewNote(kind) {
    if (noteShown) return;
    const note = $("#previewNote");
    if (!note) return;
    let dismissed = false;
    try { dismissed = sessionStorage.getItem("vsa:hideNotice") === "1"; } catch (e) { /* 隐私模式 */ }
    if (dismissed) return;
    const title = $("#previewNoteTitle");
    const body = $("#previewNoteBody");
    if (kind === "files") {
      title.textContent = "预览图没能加载";
      body.innerHTML = "页面读到了文字和提示词，但读不到图片。多半是 <code>images/</code> 文件夹没有和 <code>index.html</code> 放在一起，或者文件夹被移动、改名了。确认整个 visual-atlas 文件夹完整，再刷新页面。";
    }
    note.hidden = false;
    noteShown = true;
  }

  // Safari 对 file:// 的 history 限制更严，统一兜底
  function pushHash(hash, state) {
    try { history.pushState(state || null, "", hash); }
    catch (e) { location.hash = hash.replace(/^#/, ""); }
  }
  function replaceHash(hash) {
    try { history.replaceState(history.state, "", hash); }
    catch (e) { /* 忽略：不影响阅读 */ }
  }

  /* ---------------- 初始化界面 ---------------- */
  function initMeta() {
    const n = DATA.length;
    const h = DATA.filter((e) => e.kind === "historical").length;
    const d = DATA.filter((e) => e.kind === "digital").length;
    if (META.count) {
      $("#statTotal").textContent = META.count;
      $("#statHist").textContent = META.historical;
      $("#statDigit").textContent = META.digital;
      $("#heroCount").textContent = META.count;
      if ($("#aboutTotal")) $("#aboutTotal").textContent = META.count;
      if ($("#aboutHist")) $("#aboutHist").textContent = META.historical;
      if ($("#aboutDigit")) $("#aboutDigit").textContent = META.digital;
    } else {
      $("#statTotal").textContent = n;
      $("#statHist").textContent = h;
      $("#statDigit").textContent = d;
      $("#heroCount").textContent = n;
    }

    const decades = Array.from(new Set(DATA.map((e) => e.decade).filter(Boolean)))
      .sort((a, b) => yearOf({ decade: a }) - yearOf({ decade: b }));
    const dsel = $("#decade");
    decades.forEach((dec) => {
      const o = document.createElement("option");
      o.value = dec; o.textContent = dec;
      dsel.appendChild(o);
    });

    if (DATA.some((e) => e.custom)) {
      const chips = $(".chips");
      const b = document.createElement("button");
      b.type = "button";
      b.className = "chip";
      b.dataset.kind = "custom";
      b.textContent = "自建";
      chips.insertBefore(b, chips.lastElementChild);
    }

    const csel = $("#chapter");
    CHAPTERS.forEach((c) => {
      const o = document.createElement("option");
      o.value = String(c.chapter);
      o.textContent = "第" + c.chapter + "章 · " + c.zh + "（" + c.count + "）";
      csel.appendChild(o);
    });

    $("#aboutMeta").textContent =
      "数据抓取于 " + (META.generated || "—") + " · 共 " + (META.count || n) + " 条 · 图片来源与授权见每条详情";
  }

  /* ---------------- 渲染 ---------------- */
  function computeView() {
    const q = norm(state.q).trim();
    const tokens = q ? q.split(/\s+/).filter(Boolean) : [];
    const list = DATA.filter((e) => {
      if (state.kind === "fav" && !favs.has(e.slug)) return false;
      if (state.kind !== "all" && state.kind !== "fav" && e.kind !== state.kind) return false;
      if (state.decade && e.decade !== state.decade) return false;
      if (state.chapter && String(e.chapter) !== state.chapter) return false;
      if (tokens.length) {
        const blob = searchBlob(e);
        for (const t of tokens) if (blob.indexOf(t) === -1) return false;
      }
      return true;
    });

    if (state.sort === "title") {
      list.sort((a, b) => a.title.localeCompare(b.title, "en"));
    } else if (state.sort === "era-desc" || state.sort === "era-asc") {
      const dir = state.sort === "era-desc" ? -1 : 1;
      list.sort((a, b) => {
        const ya = yearOf(a), yb = yearOf(b);
        if (ya == null && yb == null) return byPlate(a, b);
        if (ya == null) return 1;
        if (yb == null) return -1;
        if (ya !== yb) return (ya - yb) * dir;
        return byPlate(a, b);
      });
    } else {
      list.sort(byPlate);
    }
    return list;
  }

  function cardHTML(e) {
    const ch = chapterOf(e);
    const metaRight = ch ? ch.zh : "";
    const src = e.image ? encodeURI(e.image) : "";
    const plate = String(e.plate || 0).padStart(3, "0");
    const fav = favs.has(e.slug);
    const img = src
      ? '<img src="' + esc(src) + '" alt="' + esc(e.title) + ' 的预览图" loading="lazy" decoding="async" data-img>'
      : '<div class="plate-missing">' + (IN_PREVIEW ? "在浏览器打开查看" : "预览图暂缺") + "</div>";
    return (
      '<article class="card' + (e.custom ? " is-custom" : "") + '" data-slug="' + esc(e.slug) + '">' +
        '<a class="card-link" href="#style/' + encodeURIComponent(e.slug) + '" aria-label="查看 ' + esc(e.title + (e.titleZh ? "（" + e.titleZh + "）" : "")) + '">' +
          '<figure class="plate">' + img +
            '<span class="plate-no">Nº ' + plate + '</span>' +
            '<span class="plate-kind">' + esc(KIND_LABEL[e.kind] || "风格") + '</span>' +
          '</figure>' +
          '<div class="card-meta"><span>' + esc(e.decade || (e.kind === "digital" ? "数字" : "—")) + "</span>" +
            (metaRight ? '<span class="cm-chapter">' + esc(metaRight) + "</span>" : "") +
          "</div>" +
          "<h3>" + esc(e.title) + "</h3>" +
          (e.titleZh ? '<p class="card-zh">' + esc(e.titleZh) + "</p>" : "") +
        "</a>" +
        '<button type="button" class="fav' + (fav ? " is-on" : "") + '" data-fav="' + esc(e.slug) + '" ' +
          'aria-pressed="' + (fav ? "true" : "false") + '" title="' + (fav ? "取消收藏" : "收藏") + '" aria-label="' + (fav ? "取消收藏 " : "收藏 ") + esc(e.title) + '">' +
          '<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 16.5S3.2 12.4 3.2 7.9A3.3 3.3 0 0 1 10 6.3a3.3 3.3 0 0 1 6.8 1.6c0 4.5-6.8 8.6-6.8 8.6z"/></svg>' +
        "</button>" +
      "</article>"
    );
  }

  function labelFor() {
    if (state.kind === "fav") return "我的收藏";
    if (state.q.trim()) return "搜索结果";
    if (state.kind === "historical") return "历史技法";
    if (state.kind === "digital") return "数字管线";
    if (state.decade) return state.decade + " 年代";
    return "全部风格";
  }

  function render(reset) {
    const grid = $("#grid");
    if (reset) {
      state.shown = BATCH;
      view = computeView();
      grid.innerHTML = "";
    }
    const slice = view.slice(0, state.shown);
    const start = grid.children.length;
    let html = "";
    for (let i = start; i < slice.length; i++) html += cardHTML(slice[i]);
    if (html) grid.insertAdjacentHTML("beforeend", html);

    const total = view.length;
    const shown = Math.min(state.shown, total);

    $("#count").innerHTML = "显示 <b>" + shown + "</b> / " + total + " 条" +
      (total !== DATA.length ? "（共 " + DATA.length + "）" : "");
    $("#gridLabel").textContent = labelFor();

    $("#empty").hidden = total !== 0;
    $("#moreWrap").hidden = shown >= total || total === 0;

    $("#favTotal").textContent = favs.size;
    $("#favFilterBtn").classList.toggle("is-active", state.kind === "fav");

    if (location.hash.indexOf("#style/") !== 0) {
      // 详情打开时不要把焦点抢走
    }
  }

  function setKind(kind) {
    state.kind = kind;
    $$(".chip").forEach((b) => {
      const on = b.dataset.kind === kind;
      b.classList.toggle("is-on", on);
      b.setAttribute("aria-pressed", on ? "true" : "false");
    });
    render(true);
  }

  /* ---------------- 详情 ---------------- */
  const dialog = $("#detail");
  const shell = $(".detail-shell", dialog);

  function sectionHTML(titleZh, titleEn, text) {
    if (!text) return "";
    return '<section class="d-section"><h4>' + esc(titleZh) + ' <span class="en">' + esc(titleEn) + "</span></h4><p>" + esc(text) + "</p></section>";
  }

  function detailHTML(e) {
    const ch = chapterOf(e);
    const plate = String(e.plate || 0).padStart(3, "0");
    const kind = KIND_LABEL[e.kind] || "风格";
    const crumbs = ['Nº ' + plate, kind, e.decade || "", ch ? "第" + ch.chapter + "章 · " + ch.zh : ""].filter(Boolean);
    const metaBits = [kind, e.decade || "", ch ? ch.zh : ""].filter(Boolean);

    const body = (e.body || []).map((b) => (
      '<section class="d-section"><h4>' + esc(BODY_LABEL[b.label] || b.label) +
      ' <span class="en">' + esc(BODY_EN[b.label] || b.label) + "</span></h4><p>" + esc(b.text) + "</p></section>"
    )).join("");

    const tags = (e.highlights || []).length
      ? '<div class="d-tagline">' + e.highlights.map((h) => "<span>" + esc(h) + "</span>").join("") + "</div>"
      : "";

    const terms = (e.margin || []).length
      ? '<section class="d-section"><h4>术语 <span class="en">Marginal terms</span></h4><dl class="terms">' +
        e.margin.map((m) => "<div><dt>" + esc(m.term) + "</dt><dd>" + esc(m.note) + "</dd></div>").join("") +
        "</dl></section>"
      : "";

    const sources = (e.sources || []).length
      ? '<section class="d-section"><h4>原文出处 <span class="en">Sources</span></h4><ul class="d-sources">' +
        e.sources.map((s) => '<li><a href="' + esc(s.url) + '" target="_blank" rel="noreferrer">' + esc(s.label) + "</a></li>").join("") +
        "</ul></section>"
      : "";

    const captionSec = e.caption
      ? '<section class="d-section"><h4>画面说明 <span class="en">Caption</span></h4><p>' + esc(e.caption) + "</p></section>"
      : "";

    const img = e.image
      ? (IN_PREVIEW ? "" : '<img class="d-bg" src="' + esc(encodeURI(e.image)) + '" alt="" aria-hidden="true">') +
        '<img class="d-fg" src="' + esc(encodeURI(e.image)) + '" alt="' + esc(e.title) + ' 的预览图">'
      : '<div class="plate-missing">' + (IN_PREVIEW ? "在浏览器打开查看" : "预览图暂缺") + "</div>";

    const articleUrl = esc(e.article || "https://atlas.letz.ai");

    return (
      '<div class="d-topbar">' +
        '<button type="button" class="d-back" data-back>' +
          '<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M11 4l-6 6 6 6"/></svg>全部风格</button>' +
        '<div class="d-crumb">' + crumbs.map((c) => esc(c)).join('<span class="sep">/</span>') + "</div>" +
        '<div class="d-tools"><div class="d-nav">' +
          '<button type="button" data-prev aria-label="上一条"><svg viewBox="0 0 20 20"><path d="M12 4l-6 6 6 6"/></svg></button>' +
          '<button type="button" data-next aria-label="下一条"><svg viewBox="0 0 20 20"><path d="M8 4l6 6-6 6"/></svg></button>' +
        "</div>" +
        '<button type="button" class="detail-close" data-close aria-label="关闭（Esc）">' +
          '<svg viewBox="0 0 20 20"><path d="M5 5l10 10M15 5L5 15"/></svg></button>' +
        "</div>" +
      "</div>" +
      '<figure class="d-hero">' + img + "</figure>" +
      '<div class="d-wrap">' +
        '<div class="d-head">' +
          "<div>" +
            '<div class="d-eyebrow">' + metaBits.map((m) => "<span>" + esc(m) + "</span>").join('<span class="sep">/</span>') + "</div>" +
            '<h2 id="detailTitle">' + esc(e.title) + "</h2>" +
            (e.titleZh ? '<p class="d-title-zh">' + esc(e.titleZh) + "</p>" : "") +
            (e.dating ? '<p class="d-dating">' + esc(e.dating) + "</p>" : "") +
            tags +
          "</div>" +
          "<div>" +
            '<div class="d-prompt">' +
              '<div class="d-prompt-head"><span class="lbl">LetzAI prompt · 英文原文</span>' +
                '<button type="button" class="copy-btn" data-copy>' + (e.prompt ? "复制提示词" : "暂无") + "</button></div>" +
              "<p>" + esc(e.prompt || "这条还没有整理到提示词。") + "</p>" +
            "</div>" +
            '<p class="d-credit"><span>' + (e.credit ? "图片：" + esc(e.credit.replace(/^image:\s*/i, "")) : "") + "</span>" +
              '<a href="' + articleUrl + '" target="_blank" rel="noreferrer">原站条目 ↗</a></p>' +
          "</div>" +
        "</div>" +
        '<div class="d-sections">' + body + captionSec +
          sectionHTML("区别", "Distinction", e.distinction) +
          sectionHTML("影响", "Aftermath", e.aftermath) +
          sectionHTML("冷知识", "Fun fact", e.funFact) +
          terms + sources +
        "</div>" +
        '<div class="d-foot">' +
          '<a class="d-original" href="' + articleUrl + '" target="_blank" rel="noreferrer">在原站查看 ↗</a>' +
          '<span class="d-hint">← → 切换风格 · Esc 关闭</span>' +
        "</div>" +
      "</div>"
    );
  }

  function findIndex(slug) {
    for (let i = 0; i < view.length; i++) if (view[i].slug === slug) return i;
    return -1;
  }

  function openDetail(slug, push) {
    const e = DATA.find((x) => x.slug === slug);
    if (!e) return;
    currentSlug = slug;
    $("#detailBody").innerHTML = detailHTML(e);
    shell.scrollTop = 0;

    if (!dialog.open) {
      if (typeof dialog.showModal === "function") dialog.showModal();
      else dialog.setAttribute("open", "");
      document.documentElement.classList.add("dlg-open");
    }
    if (push && location.hash !== "#style/" + slug) {
      pushHash("#style/" + slug, { vsa: 1 });
    }
    // 预取相邻条目
    const i = findIndex(slug);
    [view[i - 1], view[i + 1]].forEach((n) => {
      if (n && n.image) { const im = new Image(); im.src = encodeURI(n.image); }
    });
  }

  function closeDetail() {
    if (!dialog.open) return;
    if (typeof dialog.close === "function") dialog.close();
    else dialog.removeAttribute("open");
    document.documentElement.classList.remove("dlg-open");
    currentSlug = null;
    if (location.hash.indexOf("#style/") === 0) {
      if (history.state && history.state.vsa) { try { history.back(); } catch (e) { replaceHash("#grid"); } }
      else replaceHash(location.pathname + location.search + "#grid");
    }
  }

  function step(dir) {
    const i = findIndex(currentSlug);
    if (i < 0) return;
    const next = view[(i + dir + view.length) % view.length];
    if (!next) return;
    openDetail(next.slug, false);
    replaceHash("#style/" + next.slug);
  }

  function copyPrompt(text, btn) {
    if (!text) return;
    const done = (ok) => {
      if (!ok) return;
      const old = btn.textContent;
      btn.textContent = "已复制";
      btn.classList.add("is-done");
      setTimeout(() => { btn.textContent = old; btn.classList.remove("is-done"); }, 1600);
    };
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).then(() => done(true)).catch(() => done(fallbackCopy(text)));
    } else {
      done(fallbackCopy(text));
    }
  }
  function fallbackCopy(text) {
    try {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.setAttribute("readonly", "");
      ta.style.cssText = "position:fixed;left:-9999px;top:0;opacity:0";
      document.body.appendChild(ta);
      ta.select();
      const ok = document.execCommand("copy");
      document.body.removeChild(ta);
      return ok;
    } catch (e) { return false; }
  }

  /* ---------------- 事件 ---------------- */
  function bind() {
    // 搜索（防抖）
    let t = null;
    $("#q").addEventListener("input", (ev) => {
      const val = ev.target.value;
      clearTimeout(t);
      t = setTimeout(() => { state.q = val; render(true); }, 130);
    });

    $$(".chip").forEach((b) => {
      b.setAttribute("aria-pressed", b.classList.contains("is-on") ? "true" : "false");
      b.addEventListener("click", () => setKind(b.dataset.kind));
    });

    $("#decade").addEventListener("change", (e) => { state.decade = e.target.value; render(true); });
    $("#chapter").addEventListener("change", (e) => { state.chapter = e.target.value; render(true); });
    $("#sort").addEventListener("change", (e) => { state.sort = e.target.value; render(true); });

    $("#resetBtn").addEventListener("click", resetAll);

    const noteClose = $("#previewNoteClose");
    if (noteClose) noteClose.addEventListener("click", () => {
      $("#previewNote").hidden = true;
      try { sessionStorage.setItem("vsa:hideNotice", "1"); } catch (e) { /* 忽略 */ }
    });

    $("#moreBtn").addEventListener("click", () => {
      state.shown += BATCH;
      render(false);
    });

    // 无限加载：滚到底部自动补一批
    if ("IntersectionObserver" in window) {
      const io = new IntersectionObserver((entries) => {
        if (entries.some((en) => en.isIntersecting) && state.shown < view.length) {
          state.shown += BATCH;
          render(false);
        }
      }, { rootMargin: "800px 0px" });
      io.observe($("#moreWrap"));
    }

    $("#grid").addEventListener("click", (ev) => {
      const favBtn = ev.target.closest("[data-fav]");
      if (favBtn) {
        ev.preventDefault();
        toggleFav(favBtn.dataset.fav);
        return;
      }
      const link = ev.target.closest("a.card-link");
      if (link) {
        // 交给 hash 路由处理
        ev.preventDefault();
        const slug = link.closest("[data-slug]").dataset.slug;
        openDetail(slug, true);
      }
    });

    $("#favFilterBtn").addEventListener("click", () => {
      setKind(state.kind === "fav" ? "all" : "fav");
      $("#controls").scrollIntoView({ block: "start", behavior: "smooth" });
    });

    $$('a[href="#about"]').forEach((a) => {
      a.addEventListener("click", (ev) => {
        ev.preventDefault();
        if (state.shown < view.length) {
          state.shown = view.length;
          render(false);
        }
        requestAnimationFrame(() => {
          $("#about").scrollIntoView({ block: "start", behavior: "instant" });
        });
        replaceHash("#about");
      });
    });

    $("#randomBtn").addEventListener("click", () => {
      if (!DATA.length) return;
      const e = DATA[Math.floor(Math.random() * DATA.length)];
      openDetail(e.slug, true);
    });

    dialog.addEventListener("click", (ev) => {
      if (ev.target === dialog) { closeDetail(); return; }
      const closeBtn = ev.target.closest("[data-close],[data-back]");
      if (closeBtn) { closeDetail(); return; }
      const copyBtn = ev.target.closest("[data-copy]");
      if (copyBtn) {
        const e = DATA.find((x) => x.slug === currentSlug);
        if (e) copyPrompt(e.prompt, copyBtn);
        return;
      }
      if (ev.target.closest("[data-prev]")) step(-1);
      if (ev.target.closest("[data-next]")) step(1);
    });
    dialog.addEventListener("cancel", (ev) => {
      ev.preventDefault();
      closeDetail();
    });
    dialog.addEventListener("close", () => {
      document.documentElement.classList.remove("dlg-open");
      currentSlug = null;
    });

    document.addEventListener("keydown", (ev) => {
      const mod = ev.metaKey || ev.ctrlKey;
      if (mod && ev.key.toLowerCase() === "k") {
        ev.preventDefault();
        $("#q").focus();
        $("#q").select();
        return;
      }
      if (ev.key === "/" && !/^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName)) {
        ev.preventDefault();
        $("#q").focus();
        return;
      }
      if (dialog.open && !/^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName)) {
        if (ev.key === "ArrowLeft") { ev.preventDefault(); step(-1); }
        if (ev.key === "ArrowRight") { ev.preventDefault(); step(1); }
      }
    });

    window.addEventListener("popstate", () => {
      const slug = slugFromHash();
      if (slug) openDetail(slug, false);
      else if (dialog.open) {
        if (typeof dialog.close === "function") dialog.close();
        document.documentElement.classList.remove("dlg-open");
      }
    });

    window.addEventListener("hashchange", () => {
      const slug = slugFromHash();
      if (slug && slug !== currentSlug) openDetail(slug, false);
    });

    // 图片加载失败 → 占位
    document.addEventListener("error", (ev) => {
      const img = ev.target;
      if (img && img.tagName === "IMG" && !img.dataset.failed) {
        img.dataset.failed = "1";
        if (img.classList.contains("d-bg")) { img.style.display = "none"; return; }
        const ph = document.createElement("div");
        ph.className = "plate-missing" + (img.classList.contains("d-fg") ? " d-fg-missing" : "");
        ph.textContent = IN_PREVIEW ? "在浏览器打开查看" : "预览图暂缺";
        img.replaceWith(ph);
        imgFails += 1;
        if (imgFails >= 8) showPreviewNote(IN_PREVIEW ? "preview" : "files");
      }
    }, true);
  }

  function slugFromHash() {
    const m = location.hash.match(/^#style\/(.+)$/);
    return m ? decodeURIComponent(m[1]) : null;
  }

  function toggleFav(slug) {
    if (favs.has(slug)) favs.delete(slug); else favs.add(slug);
    writeFavs(favs);
    $$('[data-fav="' + CSS.escape(slug) + '"]').forEach((b) => {
      const on = favs.has(slug);
      b.classList.toggle("is-on", on);
      b.setAttribute("aria-pressed", on ? "true" : "false");
      b.title = on ? "取消收藏" : "收藏";
    });
    $("#favTotal").textContent = favs.size;
    if (state.kind === "fav") render(true);
  }

  function resetAll() {
    state.q = ""; state.kind = "all"; state.decade = ""; state.chapter = ""; state.sort = "plate";
    $("#q").value = ""; $("#decade").value = ""; $("#chapter").value = ""; $("#sort").value = "plate";
    $$(".chip").forEach((b) => b.classList.toggle("is-on", b.dataset.kind === "all"));
    render(true);
  }

  /* ---------------- 启动 ---------------- */
  initMeta();
  bind();
  if (IN_PREVIEW) showPreviewNote("preview");
  state.shown = BATCH;
  view = computeView();
  render(true);

  if (location.hash === "#about") {
    state.shown = view.length;
    render(true);
    setTimeout(() => $("#about").scrollIntoView({ block: "start", behavior: "instant" }), 50);
  }

  const initial = slugFromHash();
  if (initial) openDetail(initial, false);

  // 暴露给调试 / 后续扩展
  window.VSA = { data: DATA, state: state, render: render, open: openDetail };
})();
