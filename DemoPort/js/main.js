/* ============================================================
   DemoPort — main.js
   의존성 없는 바닐라 JS. 각 기능은 대상 요소가 없으면 조용히 건너뜁니다.
   1. 테마 토글
   2. 모바일 내비게이션
   3. 헤더 상태 + 스크롤 진행률
   4. 스크롤 스파이
   5. 프로젝트 로드 / 필터
   6. 이메일 복사
   7. 진입 애니메이션
   8. 연도 표기
   ============================================================ */
(function () {
  "use strict";

  var root = document.documentElement;
  var prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---------- 1. 테마 토글 ---------- */
  (function initTheme() {
    var btn = document.getElementById("theme-toggle");
    if (!btn) return;

    var label = btn.querySelector(".theme-label");
    var media = window.matchMedia("(prefers-color-scheme: light)");

    function paint(theme) {
      root.setAttribute("data-theme", theme);
      var goingLight = theme === "dark";
      btn.setAttribute("aria-pressed", theme === "light" ? "true" : "false");
      btn.setAttribute("aria-label", goingLight ? "라이트 모드로 전환" : "다크 모드로 전환");
      if (label) label.textContent = goingLight ? "라이트 모드" : "다크 모드";
    }

    function stored() {
      try { return localStorage.getItem("theme"); } catch (e) { return null; }
    }

    paint(root.getAttribute("data-theme") || (media.matches ? "light" : "dark"));

    btn.addEventListener("click", function () {
      var next = root.getAttribute("data-theme") === "light" ? "dark" : "light";
      paint(next);
      try { localStorage.setItem("theme", next); } catch (e) {}
    });

    // 저장값이 없을 때만 OS 설정 변화를 따라감
    media.addEventListener("change", function (e) {
      if (!stored()) paint(e.matches ? "light" : "dark");
    });
  })();

  /* ---------- 2. 모바일 내비게이션 ---------- */
  (function initNav() {
    var toggle = document.getElementById("nav-toggle");
    var nav = document.getElementById("primary-nav");
    if (!toggle || !nav) return;

    function setOpen(open) {
      nav.classList.toggle("is-open", open);
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
      toggle.setAttribute("aria-label", open ? "메뉴 닫기" : "메뉴 열기");
    }

    toggle.addEventListener("click", function () {
      setOpen(toggle.getAttribute("aria-expanded") !== "true");
    });

    // 링크 선택 시 닫기
    nav.addEventListener("click", function (e) {
      if (e.target.closest("a")) setOpen(false);
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && nav.classList.contains("is-open")) {
        setOpen(false);
        toggle.focus();
      }
    });

    // 바깥 클릭으로 닫기
    document.addEventListener("click", function (e) {
      if (!nav.classList.contains("is-open")) return;
      if (!nav.contains(e.target) && !toggle.contains(e.target)) setOpen(false);
    });

    // 데스크톱 폭으로 돌아오면 상태 초기화
    window.matchMedia("(min-width: 769px)").addEventListener("change", function (e) {
      if (e.matches) setOpen(false);
    });
  })();

  /* ---------- 3. 헤더 상태 + 스크롤 진행률 ---------- */
  (function initScrollChrome() {
    var header = document.getElementById("site-header");
    var bar = document.getElementById("scroll-progress");
    if (!header && !bar) return;

    var ticking = false;

    function update() {
      ticking = false;
      var y = window.scrollY || window.pageYOffset;
      if (header) header.classList.toggle("is-stuck", y > 8);
      if (bar) {
        var max = document.documentElement.scrollHeight - window.innerHeight;
        bar.style.width = (max > 0 ? Math.min(y / max, 1) * 100 : 0) + "%";
      }
    }

    window.addEventListener("scroll", function () {
      if (!ticking) { ticking = true; requestAnimationFrame(update); }
    }, { passive: true });

    window.addEventListener("resize", update, { passive: true });
    update();
  })();

  /* ---------- 4. 스크롤 스파이 ---------- */
  (function initScrollSpy() {
    var links = Array.prototype.slice.call(document.querySelectorAll(".nav-list a[href^='#']"));
    if (!links.length || !("IntersectionObserver" in window)) return;

    var map = new Map();
    links.forEach(function (link) {
      var section = document.querySelector(link.getAttribute("href"));
      if (section) map.set(section, link);
    });
    if (!map.size) return;

    var visible = new Set();

    function highlight() {
      var current = null;
      map.forEach(function (link, section) {
        if (visible.has(section) && (!current || section.offsetTop < current.offsetTop)) current = section;
      });
      links.forEach(function (link) { link.classList.remove("is-current"); });
      if (current) {
        map.get(current).classList.add("is-current");
      }
    }

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) visible.add(entry.target);
        else visible.delete(entry.target);
      });
      highlight();
    }, { rootMargin: "-80px 0px -60% 0px", threshold: 0 });

    map.forEach(function (_link, section) { observer.observe(section); });
  })();

  /* ---------- 5. 프로젝트 로드 / 필터 ---------- */
  (function initProjects() {
    var grid = document.getElementById("project-grid");
    var state = document.getElementById("grid-state");
    var filters = document.getElementById("project-filters");
    var status = document.getElementById("project-status");
    if (!grid) return;

    var KIND_LABEL = { python: "Python", web: "Web", ios: "iOS" };
    var projects = [];
    var active = "all";

    function setState(message) {
      if (!state) return;
      state.textContent = message || "";
      state.hidden = !message;
    }

    function esc(value) {
      return String(value == null ? "" : value)
        .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
    }

    function safeUrl(value) {
      var url = String(value || "").trim();
      return /^(https?:|mailto:|\/|\.\/|#)/i.test(url) ? url : "#";
    }

    function card(p) {
      var kind = KIND_LABEL[p.category] || p.category || "";
      var thumb = p.thumbnail
        ? '<img src="' + esc(p.thumbnail) + '" alt="' + esc(p.title) + ' 화면" loading="lazy" decoding="async" width="640" height="360">'
        : "";

      var tags = (p.tech || []).map(function (t) {
        return "<li>" + esc(t) + "</li>";
      }).join("");

      var links = (p.links || []).filter(function (l) { return l && l.url; }).map(function (l) {
        return '<a href="' + esc(safeUrl(l.url)) + '" target="_blank" rel="noopener">' + esc(l.label || "링크") + "</a>";
      }).join("");

      var el = document.createElement("article");
      el.className = "project-card reveal";
      el.setAttribute("data-category", p.category || "");
      el.innerHTML =
        '<div class="project-thumb">' + thumb +
          (kind ? '<span class="project-kind">' + esc(kind) + "</span>" : "") +
        "</div>" +
        '<div class="project-body">' +
          '<h3 class="project-title">' + esc(p.title) + "</h3>" +
          '<p class="project-summary">' + esc(p.summary) + "</p>" +
          (p.role ? '<p class="project-role"><strong>담당 역할</strong>' + esc(p.role) + "</p>" : "") +
          (tags ? '<ul class="project-tags" aria-label="사용 기술">' + tags + "</ul>" : "") +
          (links ? '<p class="project-links">' + links + "</p>" : "") +
        "</div>";
      return el;
    }

    function render() {
      var list = active === "all"
        ? projects
        : projects.filter(function (p) { return p.category === active; });

      grid.textContent = "";

      if (!list.length) {
        setState("해당 분야의 프로젝트가 아직 없습니다.");
      } else {
        setState("");
        var frag = document.createDocumentFragment();
        list.forEach(function (p) { frag.appendChild(card(p)); });
        grid.appendChild(frag);
        revealIn(grid);
      }

      if (status) {
        status.textContent = list.length
          ? "프로젝트 " + list.length + "건을 표시합니다."
          : "표시할 프로젝트가 없습니다.";
      }
    }

    if (filters) {
      filters.addEventListener("click", function (e) {
        var btn = e.target.closest(".filter");
        if (!btn) return;
        active = btn.getAttribute("data-filter") || "all";
        Array.prototype.forEach.call(filters.querySelectorAll(".filter"), function (b) {
          var on = b === btn;
          b.classList.toggle("is-active", on);
          b.setAttribute("aria-pressed", on ? "true" : "false");
        });
        render();
      });
    }

    fetch("data/projects.json", { cache: "no-cache" })
      .then(function (res) {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json();
      })
      .then(function (data) {
        projects = Array.isArray(data) ? data : (data.projects || []);
        render();
      })
      .catch(function (err) {
        setState("프로젝트 목록을 불러오지 못했습니다. 로컬에서 확인하는 경우 정적 서버로 실행해 주세요 (예: python -m http.server).");
        if (window.console) console.error("projects.json 로드 실패:", err);
      });
  })();

  /* ---------- 6. 이메일 복사 ---------- */
  (function initCopyEmail() {
    var btn = document.getElementById("copy-email");
    var feedback = document.getElementById("copy-feedback");
    if (!btn) return;

    var timer;

    function say(message) {
      if (!feedback) return;
      feedback.textContent = message;
      clearTimeout(timer);
      timer = setTimeout(function () { feedback.textContent = ""; }, 2600);
    }

    function fallbackCopy(text) {
      var ta = document.createElement("textarea");
      ta.value = text;
      ta.setAttribute("readonly", "");
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      var ok = false;
      try { ok = document.execCommand("copy"); } catch (e) { ok = false; }
      document.body.removeChild(ta);
      return ok;
    }

    btn.addEventListener("click", function () {
      var email = btn.getAttribute("data-email") || "";
      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(email).then(
          function () { say("복사했습니다"); },
          function () { say(fallbackCopy(email) ? "복사했습니다" : "복사에 실패했습니다"); }
        );
      } else {
        say(fallbackCopy(email) ? "복사했습니다" : "복사에 실패했습니다");
      }
    });
  })();

  /* ---------- 7. 진입 애니메이션 ---------- */
  var revealIn = function () {};

  (function initReveal() {
    if (prefersReducedMotion || !("IntersectionObserver" in window)) {
      // 애니메이션 없이 즉시 표시
      revealIn = function (scope) {
        (scope || document).querySelectorAll(".reveal").forEach(function (el) {
          el.classList.add("is-visible");
        });
      };
      revealIn(document);
      return;
    }

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
      });
    }, { rootMargin: "0px 0px -8% 0px", threshold: .08 });

    revealIn = function (scope) {
      (scope || document).querySelectorAll(".reveal:not(.is-visible)").forEach(function (el) {
        observer.observe(el);
      });
    };

    // 섹션 콘텐츠에 기본 적용
    document.querySelectorAll(
      ".about-grid, .skill-card, .timeline-item, .contact-card, .section-lede"
    ).forEach(function (el) { el.classList.add("reveal"); });

    revealIn(document);
  })();

  /* ---------- 8. 연도 표기 ---------- */
  (function initYear() {
    var el = document.getElementById("year");
    if (el) el.textContent = String(new Date().getFullYear());
  })();
})();
