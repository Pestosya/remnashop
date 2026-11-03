// H2O FreeNet landing: live plans from the bot's public API, small UI touches.
// The HTML already holds a complete fallback copy, so a failed request changes nothing.
(function () {
  "use strict";
  document.documentElement.classList.add("js");

  var PLANS_URL = "/api/v1/public/plans/public";
  var STORE_URL = "/app/store";
  var FLAG_RE = /[\u{1F1E6}-\u{1F1FF}]{2}/gu;
  var EMOJI_RE = /[\p{Extended_Pictographic}‍️]+/gu;

  function plural(n, one, few, many) {
    var m10 = n % 10, m100 = n % 100;
    if (m10 === 1 && m100 !== 11) return one;
    if (m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14)) return few;
    return many;
  }
  function devices(n) { return n + " " + plural(n, "устройство", "устройства", "устройств"); }
  function days(n) { return n + " " + plural(n, "день", "дня", "дней"); }
  function rub(value) { return Math.round(Number(value)).toLocaleString("ru-RU"); }
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function cleanName(name) { return name.replace(EMOJI_RE, "").replace(/\s+/g, " ").trim(); }
  function setText(id, text) { var el = document.getElementById(id); if (el) el.textContent = text; }

  function renderPlans(plans) {
    var list = document.getElementById("plans-list");
    if (!list || !plans.length) return;
    var hot = plans.length === 3 ? 1 : -1;
    list.innerHTML = plans.map(function (p, i) {
      var name = cleanName(p.name);
      var href = STORE_URL + "?plan=" + encodeURIComponent(p.public_code);
      var total = p.max_duration_price_rub && p.max_duration_days
        ? rub(p.max_duration_price_rub) + " ₽ за " + days(p.max_duration_days) : "";
      var traffic = p.traffic_limit ? p.traffic_limit + " ГБ трафика" : "Без лимита трафика";
      return '<article class="plan' + (i === hot ? " plan--hot" : "") + ' reveal is-in">' +
        (i === hot ? '<p class="plan__badge">Популярный</p>' : "") +
        '<h3 class="plan__name">' + esc(name) + "</h3>" +
        '<p class="plan__devices">' + esc(devices(p.device_limit)) + "</p>" +
        '<p class="plan__price"><span class="plan__from">от</span> ' + rub(p.monthly_from_rub) +
        ' <span class="plan__unit">₽/мес</span></p>' +
        '<p class="plan__total">' + esc(total) + "</p>" +
        '<ul class="plan__list"><li>Все серверы в Европе</li><li>LTE‑серверы</li><li>' + esc(traffic) + "</li></ul>" +
        '<a class="btn ' + (i === hot ? "btn--primary" : "btn--ghost") + ' btn--block" href="' + esc(href) + '">Выбрать</a>' +
        "</article>";
    }).join("");
  }

  // Countries come from the plan description (the bot writes the plan's servers there),
  // so the landing follows the fleet without edits.
  function renderCountries(plans) {
    var flags = [], names = [];
    plans.forEach(function (p) {
      (p.description || "").split("\n").forEach(function (line) {
        var found = line.match(FLAG_RE) || [];
        found.forEach(function (f) { if (f !== "🇪🇺" && flags.indexOf(f) < 0) flags.push(f); });
        var plain = line.replace(EMOJI_RE, "").replace(FLAG_RE, "").trim();
        if (found.length && found[0] !== "🇪🇺" && plain && plain.indexOf("|") < 0 && !/^Авто/i.test(plain)
            && names.indexOf(plain) < 0) names.push(plain);
      });
    });
    if (flags.length) setText("feat-flags", flags.join(" "));
    if (names.length) setText("feat-countries", names.join(", "));
  }

  function renderNumbers(plans) {
    var minMonthly = Math.min.apply(null, plans.map(function (p) { return Number(p.monthly_from_rub); }));
    var counts = plans.map(function (p) { return p.device_limit; }).filter(Boolean);
    if (isFinite(minMonthly)) setText("strip-price", "от " + rub(minMonthly) + " ₽");
    if (counts.length) {
      var max = Math.max.apply(null, counts), min = Math.min.apply(null, counts);
      setText("strip-devices", "до " + max);
      setText("hero-devices", "до " + max);
      setText("feat-devices", min === max ? devices(max) : "от " + min + " до " + max + " устройств");
      setText("faq-devices", plans.map(function (p, i) {
        return (i === 0 ? "«" + cleanName(p.name) + "» — " + devices(p.device_limit)
                        : "«" + cleanName(p.name) + "» — " + p.device_limit);
      }).join(", ") + ". Устройства можно отвязать в личном кабинете.");
    }
  }

  function loadPlans() {
    if (!window.fetch) return;
    fetch(PLANS_URL, { credentials: "omit" })
      .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
      .then(function (data) {
        var plans = (data && data.plans) || [];
        if (!plans.length) return;
        renderPlans(plans);
        renderCountries(plans);
        renderNumbers(plans);
      })
      .catch(function () { /* keep the fallback copy */ });
  }

  function navShadow() {
    var nav = document.querySelector(".nav");
    if (!nav) return;
    var on = function () { nav.classList.toggle("is-scrolled", window.scrollY > 8); };
    on();
    window.addEventListener("scroll", on, { passive: true });
  }

  function reveal() {
    var items = document.querySelectorAll(".reveal");
    if (!("IntersectionObserver" in window)) {
      items.forEach(function (el) { el.classList.add("is-in"); });
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add("is-in"); io.unobserve(e.target); }
      });
    }, { rootMargin: "0px 0px -8% 0px" });
    items.forEach(function (el) { io.observe(el); });
  }

  document.addEventListener("DOMContentLoaded", function () {
    setText("year", String(new Date().getFullYear()));
    navShadow();
    reveal();
    loadPlans();
  });
})();
