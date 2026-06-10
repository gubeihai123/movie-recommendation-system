const state = {
  user: null,
  admin: null,
  categories: [],
  currentView: "home",
  moviePage: 1,
  moviePageSize: 100,
  movieTotal: 0,
  currentMovieId: null,
  movieLoaded: false,
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));
const API_BASE = (window.MOVIE_API_BASE || "").replace(/\/$/, "");

function apiUrl(url) {
  if (/^https?:\/\//i.test(url)) return url;
  return `${API_BASE}${url}`;
}

function assetUrl(url = "") {
  if (!url || /^https?:\/\//i.test(url) || !API_BASE) return url;
  return `${API_BASE}${url.startsWith("/") ? url : `/${url}`}`;
}

const api = async (url, options = {}) => {
  const response = await fetch(apiUrl(url), {
    credentials: API_BASE ? "include" : "same-origin",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.message || "请求失败");
  }
  return data;
};

function toast(message) {
  const el = $("#toast");
  el.textContent = message;
  el.classList.add("show");
  window.clearTimeout(toast.timer);
  toast.timer = window.setTimeout(() => el.classList.remove("show"), 2200);
}

function fmt(value, digits = 1) {
  const number = Number(value || 0);
  return Number.isFinite(number) ? number.toFixed(digits) : "0.0";
}

function setMeter(prefix, value) {
  const clamped = Math.max(0, Math.min(100, value));
  $(`#${prefix}Weight`).textContent = `${clamped}%`;
  $(`#${prefix}Meter`).value = clamped;
}

function showView(view) {
  state.currentView = view;
  $$("[data-view-panel]").forEach((panel) => {
    panel.classList.toggle("active", panel.dataset.viewPanel === view);
  });
  $$(".nav-tab").forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.view === view);
  });
  window.scrollTo({ top: 0, behavior: "smooth" });

  if (view === "recommend") loadRecommendations(false).catch((error) => toast(error.message));
  if (view === "movies") {
    if (state.movieLoaded) hydratePosters($("#movieGrid"));
    else loadMovies().catch((error) => toast(error.message));
  }
  if (view === "behavior") loadBehaviors().catch((error) => toast(error.message));
  if (view === "admin") loadAdminStats().catch((error) => toast(error.message));
}

function posterTone(id) {
  const tones = [
    ["#00eaff", "#8b5cf6"],
    ["#38f8a0", "#00eaff"],
    ["#ff4fd8", "#8b5cf6"],
    ["#fbbf24", "#ff4fd8"],
    ["#22c55e", "#0f172a"],
  ];
  return tones[id % tones.length];
}

function fallbackPosterStyle(movieId) {
  const [a, b] = posterTone(movieId || 1);
  return `background:linear-gradient(135deg, ${a}55, ${b}44), linear-gradient(45deg, #111827, #020617);`;
}

function escapeHtml(value = "") {
  return String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[char]);
}

function posterImageStyle(url) {
  const resolvedUrl = assetUrl(url);
  return `background-image:linear-gradient(to top, rgba(2,6,23,0.56), rgba(2,6,23,0.02)), url('${resolvedUrl.replace(/'/g, "%27")}');`;
}

function posterBackground(item, movieId) {
  const posterUrl = item.poster_url || "";
  if (!posterUrl) {
    return fallbackPosterStyle(movieId);
  }
  return posterImageStyle(posterUrl);
}

function loadPosterElement(element) {
  const posterUrl = element.dataset.posterUrl;
  if (!posterUrl || element.classList.contains("poster-loaded")) return;
  element.style.cssText = posterImageStyle(posterUrl);
  element.classList.add("poster-loaded");
}

function hydratePosters(root = document) {
  const posters = Array.from(root.querySelectorAll("[data-poster-url]:not(.poster-loaded)"));
  if (!posters.length) return;
  if (!("IntersectionObserver" in window)) {
    posters.forEach(loadPosterElement);
    return;
  }
  if (!hydratePosters.observer) {
    hydratePosters.observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        loadPosterElement(entry.target);
        hydratePosters.observer.unobserve(entry.target);
      });
    }, { rootMargin: "520px 0px" });
  }
  posters.forEach((poster) => hydratePosters.observer.observe(poster));
}

function initParticleBackground() {
  if (!$("#tsparticles") || !window.tsParticles || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  window.tsParticles.load({
    id: "tsparticles",
    options: {
      fpsLimit: 60,
      detectRetina: true,
      background: { color: "transparent" },
      fullScreen: { enable: false },
      particles: {
        number: {
          value: 260,
          density: { enable: true, area: 900 },
        },
        color: {
          value: ["#00eaff", "#8b5cf6", "#38f8a0", "#ff4fd8", "#f8fafc"],
        },
        shape: {
          type: ["circle", "char"],
          options: {
            char: {
              value: ["0", "1", "+", "*"],
              font: "Consolas",
              style: "",
              weight: "400",
            },
          },
        },
        opacity: {
          value: { min: 0.62, max: 1 },
          animation: { enable: true, speed: 1.2, minimumValue: 0.45, sync: false },
        },
        size: {
          value: { min: 2.2, max: 8.2 },
          animation: { enable: true, speed: 2.4, minimumValue: 1.4, sync: false },
        },
        links: {
          enable: true,
          distance: 170,
          color: "#00eaff",
          opacity: 0.72,
          width: 1.55,
        },
        move: {
          enable: true,
          speed: 1.18,
          direction: "none",
          random: true,
          straight: false,
          outModes: { default: "out" },
        },
        shadow: {
          enable: true,
          color: "#00eaff",
          blur: 10,
        },
      },
      interactivity: {
        detectsOn: "window",
        events: {
          onHover: { enable: true, mode: ["grab", "repulse"] },
          onClick: { enable: true, mode: "push" },
          resize: true,
        },
        modes: {
          grab: { distance: 250, links: { opacity: 0.78 } },
          repulse: { distance: 132, duration: 0.35 },
          push: { quantity: 4 },
        },
      },
    },
  }).catch(() => {});
}

function movieCard(item, options = {}) {
  const movieId = item.movie_id;
  const score = item.recommend_score ?? item.hot_score ?? item.avg_rating ?? 0;
  const badge = options.badge || `${options.prefix || "评分"} ${fmt(score, 2)}`;
  const reason = options.reasonMode === "recommendation" ? "" : (item.description || "暂无简介");
  const category = item.category_name || "未分类";
  const rating = fmt(item.avg_rating, 1);
  const posterUrl = item.poster_url || "";
  const posterClass = posterUrl ? "poster has-image poster-lazy" : "poster";
  const posterStyle = fallbackPosterStyle(movieId);
  const posterData = posterUrl ? ` data-poster-url="${escapeHtml(posterUrl)}"` : "";
  const reasonHtml = reason ? `<p class="reason">${escapeHtml(reason)}</p>` : "";

  return `
    <article class="movie-card" data-movie-id="${movieId}">
      <div class="${posterClass}" style="${posterStyle}"${posterData}>
        <span class="rank">${escapeHtml(badge)}</span>
      </div>
      <div class="movie-body">
        <h3>${escapeHtml(item.title || "未命名电影")}</h3>
        <div class="meta">
          <span>${escapeHtml(category)}</span>
          <span>★ ${rating}</span>
        </div>
        ${reasonHtml}
        <div class="card-actions">
          <button class="mini-btn" data-action="rate" data-id="${movieId}">评分</button>
          <button class="mini-btn" data-action="favorite" data-id="${movieId}">收藏</button>
          <button class="mini-btn" data-action="detail" data-id="${movieId}">浏览</button>
        </div>
      </div>
    </article>
  `;
}

async function openMovieDetail(id) {
  const data = await api(`/api/movies/${id}`);
  const movie = data.movie;
  state.currentMovieId = movie.movie_id;
  const posterStyle = posterBackground(movie, movie.movie_id);
  const rating = fmt(movie.avg_rating, 1);
  const userScore = data.user_state?.rating_score ? `已评分 ${fmt(data.user_state.rating_score, 1)}` : "未评分";
  const favored = data.user_state?.favored ? "已收藏" : "收藏";

  $("#detailHero").setAttribute("style", posterStyle);
  $("#detailPoster").setAttribute("style", posterStyle);
  $("#detailTitle").textContent = movie.title || "未命名电影";
  $("#detailCategory").textContent = movie.category_name || "未分类";
  $("#detailRating").textContent = rating;
  $("#detailRatingCount").textContent = movie.rating_count || 0;
  $("#detailViews").textContent = movie.view_count || 0;
  $("#detailDescription").textContent = movie.description || "暂无简介";
  $("#detailUserScore").textContent = userScore;
  $("#detailFavoriteBtn").textContent = favored;
  $("#detailRateBtn").dataset.id = movie.movie_id;
  $("#detailFavoriteBtn").dataset.id = movie.movie_id;
  showView("detail");
}

function behaviorItem(item, extra = "") {
  const posterData = item.poster_url ? ` data-poster-url="${escapeHtml(item.poster_url)}"` : "";
  return `
    <article class="behavior-item">
      <div class="tiny-poster"${posterData}></div>
      <div>
        <strong>${item.title}</strong>
        <span>${extra}</span>
      </div>
    </article>
  `;
}

function empty(text) {
  return `<div class="empty-state">${text}</div>`;
}

async function loadMe() {
  const data = await api("/api/auth/me");
  if (data.type === "user") {
    state.user = data.profile;
    state.admin = null;
  } else if (data.type === "admin") {
    state.admin = data.profile;
    state.user = null;
  } else {
    state.user = null;
    state.admin = null;
  }
  renderSession();
}

function renderSession() {
  const chip = $("#userChip");
  const loginBtn = $("#openLoginBtn");
  const logoutBtn = $("#logoutBtn");
  const registerBtn = $("#openRegisterBtn");
  const behaviorLoginBtn = $("#behaviorLoginBtn");

  if (state.user) {
    chip.textContent = state.user.username;
    $("#profileName").textContent = state.user.username;
    $("#profileText").textContent = "推荐引擎将使用你的实时行为。";
    $("#behaviorProfileName").textContent = state.user.username;
    $("#behaviorProfileText").textContent = "以下是你的评分、收藏和浏览历史。";
    loginBtn.hidden = true;
    registerBtn.hidden = true;
    logoutBtn.hidden = false;
    behaviorLoginBtn.hidden = true;
  } else if (state.admin) {
    chip.textContent = `${state.admin.username} · 管理员`;
    loginBtn.hidden = true;
    registerBtn.hidden = true;
    logoutBtn.hidden = false;
    behaviorLoginBtn.hidden = true;
    showView("admin");
  } else {
    chip.textContent = "游客";
    $("#profileName").textContent = "未登录";
    $("#profileText").textContent = "登录后查看个人行为画像。";
    $("#behaviorProfileName").textContent = "游客";
    $("#behaviorProfileText").textContent = "登录后展示你的评分、收藏和浏览记录。";
    loginBtn.hidden = false;
    registerBtn.hidden = false;
    logoutBtn.hidden = true;
    behaviorLoginBtn.hidden = false;
    if (state.currentView === "admin") showView("home");
  }
}

async function loadCategories() {
  const data = await api("/api/categories");
  state.categories = data.items || [];
  const select = $("#categorySelect");
  select.innerHTML = `<option value="">全部分类</option>` + state.categories
    .map((item) => `<option value="${item.category_id}">${item.category_name}</option>`)
    .join("");
}

async function loadMovies() {
  state.moviePage = 1;
  const q = $("#searchInput").value.trim();
  const categoryId = $("#categorySelect").value;

  const fetchPage = async (page) => {
    const query = new URLSearchParams({
      page: String(page),
      page_size: String(state.moviePageSize),
    });
    if (q) query.set("q", q);
    if (categoryId) query.set("category_id", categoryId);
    return api(`/api/movies?${query.toString()}`);
  };

  const firstPage = await fetchPage(1);
  const total = Number(firstPage.total || 0);
  const items = [...(firstPage.items || [])];
  const totalPages = Math.ceil(total / state.moviePageSize);
  for (let page = 2; page <= totalPages; page += 1) {
    const data = await fetchPage(page);
    items.push(...(data.items || []));
  }

  state.movieTotal = total;
  const html = items.length
    ? items.map((item) => movieCard(item, { prefix: "评分", reasonMode: "description" })).join("")
    : empty("没有找到匹配的电影");
  $("#movieGrid").innerHTML = html;
  state.movieLoaded = true;
  hydratePosters($("#movieGrid"));

  $("#movieCount").textContent = total;
  $("#loadMoreMoviesBtn").hidden = true;
  const ratings = items.map((item) => Number(item.avg_rating || 0));
  const avg = ratings.length ? ratings.reduce((sum, item) => sum + item, 0) / ratings.length : 0;
  $("#avgRating").textContent = fmt(avg, 1);
}

async function loadMovieSummary() {
  const data = await api("/api/movies?page=1&page_size=1");
  $("#movieCount").textContent = data.total || 0;
  const first = data.items?.[0];
  $("#avgRating").textContent = first ? fmt(first.avg_rating, 1) : "0.0";
}

function dailyMovieHtml(item) {
  const movieId = item.movie_id;
  const category = item.category_name || "未分类";
  const posterUrl = item.poster_url || "";
  const posterStyle = posterUrl
    ? `background-image:url('${assetUrl(posterUrl).replace(/'/g, "%27")}');`
    : fallbackPosterStyle(movieId);

  return `
    <div class="daily-poster" style="${posterStyle}"></div>
    <div class="daily-info">
      <span class="daily-type">${escapeHtml(category)}</span>
      <h3>${escapeHtml(item.title || "未命名电影")}</h3>
      <span class="daily-rating">评分 ${fmt(item.avg_rating, 1)} · ${item.rating_count || 0} 人评分</span>
    </div>
    <button class="primary-btn" data-action="detail" data-id="${movieId}" type="button">浏览</button>
  `;
}

async function loadDailyMovie() {
  const summary = await api("/api/movies?page=1&page_size=1");
  const total = Number(summary.total || 0);
  if (!total) {
    $("#dailyMovieCard").innerHTML = empty("暂无可展示电影");
    return;
  }
  const daySeed = Math.floor(Date.now() / 86400000);
  const page = (daySeed % total) + 1;
  const data = await api(`/api/movies?page=${page}&page_size=1`);
  const movie = data.items?.[0] || summary.items?.[0];
  $("#dailyMovieCard").innerHTML = movie ? dailyMovieHtml(movie) : empty("暂无可展示电影");
}

async function loadHot() {
  const data = await api("/api/recommendations/hot?limit=6");
  $("#hotList").innerHTML = (data.items || [])
    .map((item, index) => `
      <div class="hot-item">
        <span>${String(index + 1).padStart(2, "0")} ${item.title}</span>
        <b>Hot ${fmt(item.hot_score, 1)}</b>
      </div>
    `)
    .join("");
}

async function loadRecommendations(refresh = false) {
  if (!state.user) {
    $("#recommendGrid").innerHTML = empty("请先登录普通用户账号生成个性化推荐");
    $("#bestScore").textContent = "0.00";
    return;
  }
  const data = await api(`/api/recommendations?limit=9${refresh ? "&refresh=1" : ""}`);
  const items = data.items || [];
  $("#recommendGrid").innerHTML = items.length
    ? items.map((item) => movieCard(item, { prefix: "推荐", reasonMode: "recommendation" })).join("")
    : empty("暂无推荐结果");
  hydratePosters($("#recommendGrid"));
  const best = items.reduce((max, item) => Math.max(max, Number(item.recommend_score || 0)), 0);
  $("#bestScore").textContent = fmt(best, 2);
  $("#recCount").textContent = `Top-${items.length || 9}`;
}

async function loadBehaviors() {
  if (!state.user) {
    setMeter("rating", 0);
    setMeter("favorite", 0);
    setMeter("browse", 0);
    $("#behaviorCount").textContent = "--";
    $("#ratingList").innerHTML = empty("登录后显示评分记录");
    $("#favoriteList").innerHTML = empty("登录后显示收藏记录");
    $("#browseList").innerHTML = empty("登录后显示浏览记录");
    return;
  }
  const data = await api("/api/me/behaviors");
  const ratingCount = data.ratings.length;
  const favoriteCount = data.favorites.length;
  const browseCount = data.browses.length;
  $("#behaviorCount").textContent = ratingCount + favoriteCount + browseCount;
  setMeter("rating", Math.min(100, ratingCount * 8));
  setMeter("favorite", Math.min(100, favoriteCount * 12));
  setMeter("browse", Math.min(100, browseCount));

  $("#ratingList").innerHTML = ratingCount
    ? data.ratings.slice(0, 12).map((item) => behaviorItem(item, `评分 ${fmt(item.score, 1)} · ${item.created_at}`)).join("")
    : empty("暂无评分记录");
  $("#favoriteList").innerHTML = favoriteCount
    ? data.favorites.slice(0, 12).map((item) => behaviorItem(item, `收藏于 ${item.created_at}`)).join("")
    : empty("暂无收藏记录");
  $("#browseList").innerHTML = browseCount
    ? data.browses.slice(0, 12).map((item) => behaviorItem(item, `浏览于 ${item.browse_time}`)).join("")
    : empty("暂无浏览记录");
  hydratePosters($("#ratingList"));
  hydratePosters($("#favoriteList"));
  hydratePosters($("#browseList"));
}

async function loadBehaviorSummary() {
  if (!state.user) {
    $("#behaviorCount").textContent = "--";
    return;
  }
  const data = await api("/api/me/behaviors");
  const ratingCount = data.ratings.length;
  const favoriteCount = data.favorites.length;
  const browseCount = data.browses.length;
  $("#behaviorCount").textContent = ratingCount + favoriteCount + browseCount;
  setMeter("rating", Math.min(100, ratingCount * 8));
  setMeter("favorite", Math.min(100, favoriteCount * 12));
  setMeter("browse", Math.min(100, browseCount));
}

async function loadAdminStats() {
  const holder = $("#adminStats");
  if (!state.admin) {
    holder.innerHTML = empty("请输入管理员账号和密码后进入后台");
    return;
  }
  const data = await api("/api/admin/stats");
  holder.innerHTML = data.table_counts
    .map((item) => `
      <article class="admin-card">
        <span>${item.table_name}</span>
        <strong>${item.total}</strong>
      </article>
    `)
    .join("");
}

async function refreshDashboard() {
  await Promise.all([loadCategories(), loadHot(), loadMovieSummary(), loadDailyMovie()]);
  await loadMe();
  if (state.user) {
    await loadBehaviorSummary();
  } else if (state.admin) {
    await loadAdminStats();
  }
}

function openLogin() {
  $("#loginTitle").textContent = "账号登录";
  $("#loginForm").dataset.mode = "login";
  $("#loginForm").username.value = "";
  $("#loginForm").password.value = "";
  $("#loginForm").email.value = "";
  $("#loginForm").email.required = false;
  $("#loginForm").password.autocomplete = "current-password";
  $("#emailField").hidden = true;
  $("#registerRules").hidden = true;
  $("#authSubmitBtn").textContent = "登录";
  $("#toggleAuthModeBtn").hidden = false;
  $("#toggleAuthModeBtn").textContent = "还没有账号？立即注册";
  $("#loginMessage").textContent = "";
  $("#loginModal").classList.add("open");
  $("#loginModal").setAttribute("aria-hidden", "false");
}

function openRegister() {
  $("#loginTitle").textContent = "用户注册";
  $("#loginForm").dataset.mode = "register";
  $("#loginForm").username.value = "";
  $("#loginForm").email.value = "";
  $("#loginForm").password.value = "";
  $("#loginForm").email.required = true;
  $("#loginForm").password.autocomplete = "new-password";
  $("#emailField").hidden = false;
  $("#registerRules").hidden = false;
  $("#authSubmitBtn").textContent = "注册并登录";
  $("#toggleAuthModeBtn").hidden = false;
  $("#toggleAuthModeBtn").textContent = "已有账号？返回登录";
  $("#loginMessage").textContent = "";
  $("#loginModal").classList.add("open");
  $("#loginModal").setAttribute("aria-hidden", "false");
}

function closeLogin() {
  $("#loginModal").classList.remove("open");
  $("#loginModal").setAttribute("aria-hidden", "true");
}

async function loginWithAutoRole(payload) {
  try {
    const data = await api("/api/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    return { type: "user", data };
  } catch (userError) {
    try {
      const data = await api("/api/auth/admin/login", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      return { type: "admin", data };
    } catch (_adminError) {
      throw userError;
    }
  }
}

async function handleMovieAction(target) {
  const action = target.dataset.action;
  const id = target.dataset.id;
  if (!action || !id) return;
  if (action === "detail") {
    await openMovieDetail(id);
    return;
  }
  if (!state.user) {
    openLogin();
    toast("请先登录普通用户账号");
    return;
  }
  if (action === "rate") {
    const score = window.prompt("请输入 1-5 分", "5");
    if (!score) return;
    await api(`/api/movies/${id}/rating`, {
      method: "POST",
      body: JSON.stringify({ score: Number(score) }),
    });
    toast("评分已保存");
  }
  if (action === "favorite") {
    await api(`/api/movies/${id}/favorite`, { method: "POST", body: "{}" });
    toast("已收藏");
  }
  if (state.currentView === "detail" && state.currentMovieId) {
    await openMovieDetail(state.currentMovieId);
  } else {
    await loadMovies();
  }
  await Promise.all([loadBehaviors(), loadRecommendations(true), loadHot()]);
}

document.addEventListener("click", async (event) => {
  const target = event.target.closest("button");
  if (!target) return;
  try {
    if (target.dataset.view) {
      showView(target.dataset.view);
    }
    if (target.id === "openLoginBtn" || target.id === "behaviorLoginBtn") openLogin();
    if (target.id === "openRegisterBtn") openRegister();
    if (target.id === "closeLoginBtn") closeLogin();
    if (target.id === "toggleAuthModeBtn") {
      const mode = $("#loginForm").dataset.mode;
      if (mode === "register") openLogin();
      else openRegister();
    }
    if (target.id === "logoutBtn") {
      await api("/api/auth/logout", { method: "POST", body: "{}" });
      state.user = null;
      state.admin = null;
      renderSession();
      await Promise.all([loadRecommendations(false), loadBehaviors(), loadAdminStats()]);
      showView("home");
      toast("已退出登录");
    }
    if (target.id === "heroRecommendBtn") {
      showView("recommend");
      if (!state.user) openLogin();
    }
    if (target.id === "heroMoviesBtn") {
      showView("movies");
    }
    if (target.id === "backToMoviesBtn") {
      showView("movies");
    }
    if (target.id === "refreshRecommendBtn") {
      if (!state.user) openLogin();
      else {
        await loadRecommendations(true);
        toast("推荐结果已刷新");
      }
    }
    if (target.id === "reloadHotBtn") {
      await loadHot();
      toast("热门榜单已更新");
    }
    await handleMovieAction(target);
  } catch (error) {
    toast(error.message);
  }
});

$("#loginModal").addEventListener("click", (event) => {
  if (event.target.id === "loginModal") closeLogin();
});

$("#loginForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const mode = form.dataset.mode || "login";
  const payload = {
    username: form.username.value.trim(),
    password: form.password.value,
  };
  if (mode === "register") {
    payload.email = form.email.value.trim();
  }
  try {
    if (mode === "register") {
      const data = await api("/api/auth/register", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      state.user = data.user;
      state.admin = null;
      renderSession();
      closeLogin();
      showView("recommend");
      await Promise.all([loadRecommendations(true), loadBehaviors(), loadAdminStats()]);
      toast("注册成功");
      return;
    }

    const result = await loginWithAutoRole(payload);
    state.user = result.type === "user" ? result.data.user : null;
    state.admin = result.type === "admin" ? result.data.admin : null;
    renderSession();
    closeLogin();
    showView(result.type === "admin" ? "admin" : "recommend");
    await Promise.all([loadRecommendations(true), loadBehaviors(), loadAdminStats()]);
    toast(result.type === "admin" ? "管理员登录成功" : "登录成功");
  } catch (error) {
    $("#loginMessage").textContent = error.message;
  }
});

$("#searchForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await loadMovies();
  } catch (error) {
    toast(error.message);
  }
});

initParticleBackground();
refreshDashboard().catch((error) => {
  $("#recommendGrid").innerHTML = empty("后端接口暂不可用");
  toast(error.message);
});
