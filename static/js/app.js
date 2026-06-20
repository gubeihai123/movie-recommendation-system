const state = {
  user: null,
  admin: null,
  currentView: "home",
  galleryMovies: [],
  currentMovieId: null,
  pendingRatingMovieId: null,
  movieLoaded: false,
  recommendationTimer: null,
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));
const API_BASE = (window.MOVIE_API_BASE || "").replace(/\/$/, "");
const AUTH_TOKEN_KEY = "movie_recsys_auth_token";
const GALLERY_LIMIT = 36;
const GALLERY_REQUEST_SIZE = 36;
if (localStorage.getItem(AUTH_TOKEN_KEY)) {
  state.user = { username: "已登录" };
}
const fallbackGalleryMovies = [
  { movie_id: 1, title: "阿甘正传", category_name: "爱情", avg_rating: 4.0, rating_count: 5, poster_url: "/static/posters/movie_001.jpg" },
  { movie_id: 2, title: "教父", category_name: "悬疑", avg_rating: 4.0, rating_count: 9, poster_url: "/static/posters/movie_002.jpg" },
  { movie_id: 4, title: "黑客帝国", category_name: "悬疑", avg_rating: 3.7, rating_count: 6, poster_url: "/static/posters/movie_004.png" },
  { movie_id: 7, title: "千与千寻", category_name: "动画", avg_rating: 3.7, rating_count: 12, poster_url: "/static/posters/movie_007.png" },
  { movie_id: 9, title: "低俗小说", category_name: "悬疑", avg_rating: 4.0, rating_count: 13, poster_url: "/static/posters/movie_009.jpg" },
  { movie_id: 14, title: "盗梦空间", category_name: "悬疑", avg_rating: 4.2, rating_count: 11, poster_url: "/static/posters/movie_014.jpg" },
  { movie_id: 17, title: "机器人总动员", category_name: "动画", avg_rating: 4.0, rating_count: 9, poster_url: "/static/posters/movie_017.jpg" },
  { movie_id: 27, title: "星际穿越", category_name: "科幻", avg_rating: 4.1, rating_count: 10, poster_url: "/static/posters/movie_027.jpg" },
  { movie_id: 36, title: "寻梦环游记", category_name: "动画", avg_rating: 4.0, rating_count: 8, poster_url: "/static/posters/movie_036.jpg" },
  { movie_id: 77, title: "龙猫", category_name: "动画", avg_rating: 4.0, rating_count: 7, poster_url: "/static/posters/movie_077.jpg" },
];

function apiUrl(url) {
  if (/^https?:\/\//i.test(url)) return url;
  return `${API_BASE}${url}`;
}

function assetUrl(url = "") {
  if (!url || /^https?:\/\//i.test(url) || !API_BASE) return url;
  if (url.startsWith("/static/posters/")) {
    return new URL(url.slice(1), document.baseURI).href;
  }
  return `${API_BASE}${url.startsWith("/") ? url : `/${url}`}`;
}

async function api(url, options = {}) {
  const token = localStorage.getItem(AUTH_TOKEN_KEY);
  const response = await fetch(apiUrl(url), {
    credentials: API_BASE ? "include" : "same-origin",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.message || "请求失败");
  return data;
}

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

function escapeHtml(value = "") {
  return String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[char]);
}

function posterUrl(item = {}) {
  return assetUrl(item.poster_url || "");
}

function fallbackPoster(movieId) {
  const hue = (Number(movieId || 1) * 47) % 360;
  return `linear-gradient(135deg, hsl(${hue} 56% 82%), hsl(${(hue + 60) % 360} 44% 92%))`;
}

function posterStyle(item = {}) {
  const url = posterUrl(item);
  return url ? `background-image:url('${url.replace(/'/g, "%27")}')` : `background:${fallbackPoster(item.movie_id)}`;
}

function rectCenterPoster() {
  const width = Math.min(220, window.innerWidth * 0.22);
  const height = width * 1.5;
  return {
    left: window.innerWidth / 2 - width / 2,
    top: window.innerHeight / 2 - height / 2,
    width,
    height,
  };
}

function animatePosterFlight(fromRect, toRect, imageUrl, reverse = false) {
  return new Promise((resolve) => {
    const clone = document.createElement("div");
    clone.className = "flight-poster";
    clone.style.left = `${fromRect.left}px`;
    clone.style.top = `${fromRect.top}px`;
    clone.style.width = `${fromRect.width}px`;
    clone.style.height = `${fromRect.height}px`;
    clone.style.backgroundImage = imageUrl ? `url("${imageUrl.replace(/"/g, "%22")}")` : "";
    document.body.appendChild(clone);

    const animation = clone.animate([
      {
        left: `${fromRect.left}px`,
        top: `${fromRect.top}px`,
        width: `${fromRect.width}px`,
        height: `${fromRect.height}px`,
        opacity: 0.96,
        filter: reverse ? "blur(0px)" : "blur(0.2px)",
        transform: reverse ? "scale(1)" : "scale(0.96)",
      },
      {
        left: `${toRect.left}px`,
        top: `${toRect.top}px`,
        width: `${toRect.width}px`,
        height: `${toRect.height}px`,
        opacity: reverse ? 0.82 : 1,
        filter: reverse ? "blur(1px)" : "blur(0px)",
        transform: reverse ? "scale(0.92)" : "scale(1.04)",
      },
    ], {
      duration: reverse ? 520 : 640,
      easing: "cubic-bezier(.2,.72,.18,1)",
      fill: "forwards",
    });

    animation.onfinish = () => {
      clone.remove();
      resolve();
    };
    animation.oncancel = () => {
      clone.remove();
      resolve();
    };
  });
}

function showView(view) {
  state.currentView = view;
  $$("[data-view-panel]").forEach((panel) => {
    panel.classList.toggle("active", panel.dataset.viewPanel === view);
  });
  renderTopActions();
  window.scrollTo({ top: 0, behavior: "smooth" });

  if (view !== "recommend") stopRecommendationProgress();
  if (view === "movies" && !state.movieLoaded) loadMovies().catch((error) => toast(error.message));
  if (view === "admin") loadAdminStats().catch((error) => toast(error.message));
}

function renderTopActions() {
  const loggedIn = Boolean(state.user);
  const adminLoggedIn = Boolean(state.admin);
  const setHidden = (selector, value) => {
    const el = $(selector);
    if (el) el.hidden = value;
  };
  setHidden("#openLoginBtn", loggedIn || adminLoggedIn);
  setHidden("#openRegisterBtn", loggedIn || adminLoggedIn);
  setHidden("#homeNavBtn", !loggedIn || state.currentView !== "recommend");
  setHidden("#logoutBtn", !loggedIn && !adminLoggedIn);
  setHidden("#heroRecommendBtn", !loggedIn || state.currentView === "recommend");
}

function sphereTransform(i, total) {
  const golden = Math.PI * (3 - Math.sqrt(5));
  const yNorm = 1 - (2 * (i + 0.5)) / total;
  const radiusAtY = Math.sqrt(1 - yNorm * yNorm);
  const theta = golden * i;
  const radius = 410;
  const x = Math.cos(theta) * radiusAtY * radius;
  const y = yNorm * radius * 0.82;
  const z = Math.sin(theta) * radiusAtY * radius;
  const ry = (theta * 180) / Math.PI + 90;
  const rx = -yNorm * 16;
  const scale = 0.78 + ((z + radius) / (radius * 2)) * 0.42;
  return `translate(-50%, -50%) translate3d(${x}px, ${y}px, ${z}px) rotateY(${ry}deg) rotateX(${rx}deg) scale(${scale})`;
}

function arcTransform(i) {
  const columns = 13;
  const col = (i % columns) - Math.floor(columns / 2);
  const row = Math.floor(i / columns) - 1;
  const angle = col * 9.5;
  const rad = (angle * Math.PI) / 180;
  const radius = 660;
  const x = Math.sin(rad) * radius;
  const z = Math.cos(rad) * radius - 620;
  const y = row * 172;
  const scale = 0.88 + (1 - Math.abs(col) / 7) * 0.16;
  return `translate(-50%, -50%) translate3d(${x}px, ${y}px, ${z}px) rotateY(${-angle}deg) scale(${scale})`;
}

function renderGallery(movies) {
  const holder = $("#movieSphere");
  const usable = movies.filter((item) => item.poster_url).slice(0, GALLERY_LIMIT);
  state.galleryMovies = usable.length ? usable : movies.slice(0, GALLERY_LIMIT);
  const total = Math.max(state.galleryMovies.length, 1);
  holder.innerHTML = state.galleryMovies.map((item, index) => {
    const isFar = index % 5 === 0 ? " is-far" : "";
    return `
      <button class="sphere-card${isFar}" type="button" data-gallery-id="${item.movie_id}"
        style="--sphere-transform:${sphereTransform(index, total)}; --arc-transform:${arcTransform(index)}">
        <img src="${escapeHtml(posterUrl(item))}" alt="${escapeHtml(item.title || "电影封面")}"
          loading="${index < 6 ? "eager" : "lazy"}" decoding="async" fetchpriority="${index < 6 ? "high" : "low"}">
      </button>
    `;
  }).join("");
}

async function focusGalleryMovie(movieId, sourceCard = null) {
  const item = state.galleryMovies.find((movie) => String(movie.movie_id) === String(movieId));
  if (!item) return;
  const imageUrl = posterUrl(item);
  if (sourceCard) {
    const fromRect = sourceCard.getBoundingClientRect();
    await animatePosterFlight(fromRect, rectCenterPoster(), imageUrl, false);
  }
  $$(".sphere-card").forEach((card) => {
    card.classList.toggle("is-active", String(card.dataset.galleryId) === String(movieId));
  });
  $("#focusPoster").setAttribute("style", posterStyle(item));
  $("#focusCategory").textContent = item.category_name || "未分类";
  $("#focusTitle").textContent = item.title || "未命名电影";
  $("#focusRating").textContent = `评分 ${fmt(item.avg_rating, 1)} · ${item.rating_count || 0} 人评分`;
  $("#focusBrowseBtn").dataset.id = item.movie_id;
  $("#focusMovieCard").hidden = false;
  $("#focusMovieCard").classList.remove("is-closing");
}

async function closeFocusMovie() {
  const card = $("#focusMovieCard");
  if (card.hidden) return;
  const movieId = $("#focusBrowseBtn").dataset.id;
  const item = state.galleryMovies.find((movie) => String(movie.movie_id) === String(movieId));
  const target = $(`[data-gallery-id="${CSS.escape(String(movieId))}"]`);
  const fromRect = $("#focusPoster").getBoundingClientRect();
  const toRect = target ? target.getBoundingClientRect() : rectCenterPoster();
  card.classList.add("is-closing");
  await animatePosterFlight(fromRect, toRect, item ? posterUrl(item) : "", true);
  card.hidden = true;
  card.classList.remove("is-closing");
  $$(".sphere-card").forEach((itemCard) => itemCard.classList.remove("is-active"));
}

async function loadGalleryMovies() {
  try {
    const data = await api(`/api/movies?page=1&page_size=${GALLERY_REQUEST_SIZE}`);
    renderGallery(data.items?.length ? data.items : fallbackGalleryMovies);
  } catch (error) {
    renderGallery(fallbackGalleryMovies);
    throw error;
  }
}

function recCard(item, index) {
  return `
    <article class="rec-card">
      <div class="rec-poster" style="${posterStyle(item)}"></div>
      <div class="rec-body">
        <span class="rec-rank">Top ${index + 1}</span>
        <h3>${escapeHtml(item.title || "未命名电影")}</h3>
        <p class="meta">${escapeHtml(item.category_name || "未分类")}</p>
        <button class="glass-btn accent full" data-action="detail" data-id="${item.movie_id}" type="button">浏览</button>
      </div>
    </article>
  `;
}

function stopRecommendationProgress() {
  if (state.recommendationTimer) {
    window.clearInterval(state.recommendationTimer);
    state.recommendationTimer = null;
  }
}

function setProgress(value) {
  const clamped = Math.max(1, Math.min(99, Math.round(value)));
  $("#recommendProgressBar").style.width = `${clamped}%`;
  $("#recommendProgressText").textContent = `${clamped}%`;
}

function delay(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function preloadImage(url, timeout = 3600) {
  if (!url) return Promise.resolve(false);
  return new Promise((resolve) => {
    const img = new Image();
    const timer = window.setTimeout(() => resolve(false), timeout);
    img.onload = () => {
      window.clearTimeout(timer);
      resolve(true);
    };
    img.onerror = () => {
      window.clearTimeout(timer);
      resolve(false);
    };
    img.src = url;
  });
}

async function pickVisibleRecommendationItems(items, limit = 5) {
  const results = await Promise.all(items.map(async (item) => ({
    item,
    ok: await preloadImage(posterUrl(item)),
  })));
  const loaded = results.filter((entry) => entry.ok).map((entry) => entry.item);
  if (loaded.length >= limit) return loaded.slice(0, limit);

  const used = new Set(loaded.map((item) => String(item.movie_id)));
  const filler = [];
  for (const item of state.galleryMovies) {
    if (used.has(String(item.movie_id))) continue;
    if (!posterUrl(item)) continue;
    filler.push(item);
    used.add(String(item.movie_id));
    if (loaded.length + filler.length >= limit) break;
  }
  return [...loaded, ...filler].slice(0, limit);
}

async function startRecommendations(refresh = true) {
  if (!state.user) {
    openLogin();
    toast("请先登录普通用户账号");
    return;
  }

  showView("recommend");
  $("#recommendLoading").hidden = false;
  $("#recommendShowcase").hidden = true;
  setProgress(1);

  let progress = 1;
  stopRecommendationProgress();
  state.recommendationTimer = window.setInterval(() => {
    progress = Math.min(99, progress + Math.max(1, Math.round((99 - progress) * 0.08)));
    setProgress(progress);
    if (progress >= 99) stopRecommendationProgress();
  }, 90);

  const request = api(`/api/recommendations?limit=20${refresh ? "&refresh=1" : ""}`);
  const [data] = await Promise.all([request, delay(1700)]);
  const items = await pickVisibleRecommendationItems(data.items || [], 5);
  stopRecommendationProgress();
  setProgress(99);

  $("#recommendGrid").innerHTML = items.length
    ? items.map(recCard).join("")
    : `<div class="empty-state">暂无推荐结果</div>`;

  await delay(260);
  $("#recommendLoading").hidden = true;
  $("#recommendShowcase").hidden = false;
}

async function openMovieDetail(id) {
  const data = await api(`/api/movies/${id}`);
  const movie = data.movie;
  state.currentMovieId = movie.movie_id;
  const rating = fmt(movie.avg_rating, 1);
  const userScore = data.user_state?.rating_score ? `已评分 ${fmt(data.user_state.rating_score, 1)}` : "未评分";
  const favored = data.user_state?.favored ? "已收藏" : "收藏";

  $("#detailPoster").setAttribute("style", posterStyle(movie));
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

function empty(text) {
  return `<div class="empty-state">${escapeHtml(text)}</div>`;
}

function movieCard(item) {
  return `
    <article class="movie-card">
      <div class="poster" style="${posterStyle(item)}"></div>
      <div class="movie-body">
        <h3>${escapeHtml(item.title || "未命名电影")}</h3>
        <p class="meta">${escapeHtml(item.category_name || "未分类")} · ★ ${fmt(item.avg_rating, 1)}</p>
        <p class="reason">${escapeHtml(item.description || "暂无简介")}</p>
        <div class="card-actions">
          <button class="mini-btn" data-action="rate" data-id="${item.movie_id}">评分</button>
          <button class="mini-btn" data-action="favorite" data-id="${item.movie_id}">收藏</button>
          <button class="mini-btn" data-action="detail" data-id="${item.movie_id}">浏览</button>
        </div>
      </div>
    </article>
  `;
}

async function loadCategories() {
  const data = await api("/api/categories");
  const select = $("#categorySelect");
  select.innerHTML = `<option value="">全部分类</option>` + (data.items || [])
    .map((item) => `<option value="${item.category_id}">${escapeHtml(item.category_name)}</option>`)
    .join("");
}

async function loadMovies() {
  const q = $("#searchInput").value.trim();
  const categoryId = $("#categorySelect").value;
  const query = new URLSearchParams({ page: "1", page_size: "100" });
  if (q) query.set("q", q);
  if (categoryId) query.set("category_id", categoryId);
  const data = await api(`/api/movies?${query.toString()}`);
  $("#movieGrid").innerHTML = (data.items || []).length
    ? data.items.map(movieCard).join("")
    : empty("没有找到匹配的电影");
  state.movieLoaded = true;
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
    localStorage.removeItem(AUTH_TOKEN_KEY);
    state.user = null;
    state.admin = null;
  }
  renderSession();
}

function renderSession() {
  const loggedIn = Boolean(state.user);
  document.body.classList.toggle("is-authenticated", loggedIn);
  $("#userChip").textContent = state.user?.username || state.admin?.username || "游客";
  renderTopActions();

  if (state.admin) showView("admin");
  if (!loggedIn && state.currentView === "recommend") showView("home");
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
        <span>${escapeHtml(item.table_name)}</span>
        <strong>${item.total}</strong>
      </article>
    `)
    .join("");
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

function setRatingPreview(score = 0) {
  const value = Number(score || 0);
  $$(".rating-star").forEach((star) => {
    star.classList.toggle("filled", Number(star.dataset.score) <= value);
  });
  $("#ratingNote").textContent = value ? `${value} 星` : "移动到星星上预览分数，点击确认评分。";
}

function openRatingModal(movieId) {
  state.pendingRatingMovieId = movieId;
  setRatingPreview(0);
  $("#ratingModal").classList.add("open");
  $("#ratingModal").setAttribute("aria-hidden", "false");
}

function closeRatingModal() {
  state.pendingRatingMovieId = null;
  setRatingPreview(0);
  $("#ratingModal").classList.remove("open");
  $("#ratingModal").setAttribute("aria-hidden", "true");
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

async function refreshAfterMovieMutation() {
  if (state.currentView === "detail" && state.currentMovieId) {
    await openMovieDetail(state.currentMovieId);
  } else if (state.movieLoaded) {
    await loadMovies();
  }
}

async function submitRating(movieId, score) {
  await api(`/api/movies/${movieId}/rating`, {
    method: "POST",
    body: JSON.stringify({ score: Number(score) }),
  });
  closeRatingModal();
  toast(`已评分 ${score} 星`);
  await refreshAfterMovieMutation();
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
    openRatingModal(id);
    return;
  }
  if (action === "favorite") {
    await api(`/api/movies/${id}/favorite`, { method: "POST", body: "{}" });
    toast("已收藏");
  }
  await refreshAfterMovieMutation();
}

document.addEventListener("click", async (event) => {
  const galleryCard = event.target.closest("[data-gallery-id]");
  if (galleryCard) {
    await focusGalleryMovie(galleryCard.dataset.galleryId, galleryCard);
    return;
  }

  if (
    state.currentView === "home"
    && !$("#focusMovieCard").hidden
    && event.target.closest(".gallery-stage")
    && !event.target.closest(".focus-movie-card")
  ) {
    await closeFocusMovie();
    return;
  }

  const target = event.target.closest("button");
  if (!target) return;
  try {
    if (target.dataset.view) showView(target.dataset.view);
    if (target.id === "openLoginBtn" || target.id === "behaviorLoginBtn") openLogin();
    if (target.id === "openRegisterBtn") openRegister();
    if (target.id === "closeLoginBtn") closeLogin();
    if (target.id === "closeFocusBtn") {
      await closeFocusMovie();
      return;
    }
    if (target.id === "toggleAuthModeBtn") {
      const mode = $("#loginForm").dataset.mode;
      if (mode === "register") openLogin();
      else openRegister();
    }
    if (target.id === "logoutBtn") {
      await api("/api/auth/logout", { method: "POST", body: "{}" });
      localStorage.removeItem(AUTH_TOKEN_KEY);
      state.user = null;
      state.admin = null;
      renderSession();
      $("#focusMovieCard").hidden = true;
      showView("home");
      toast("已退出登录");
    }
    if (target.id === "heroRecommendBtn") await startRecommendations(true);
    if (target.id === "backToMoviesBtn") showView("home");
    await handleMovieAction(target);
  } catch (error) {
    toast(error.message);
  }
});

$("#loginModal").addEventListener("click", (event) => {
  if (event.target.id === "loginModal") closeLogin();
});

$("#ratingModal").addEventListener("click", (event) => {
  if (event.target.id === "ratingModal" || event.target.id === "closeRatingBtn") {
    closeRatingModal();
  }
});

$("#ratingStars").addEventListener("pointerover", (event) => {
  const star = event.target.closest(".rating-star");
  if (star) setRatingPreview(star.dataset.score);
});

$("#ratingStars").addEventListener("pointerleave", () => setRatingPreview(0));

$("#ratingStars").addEventListener("click", async (event) => {
  const star = event.target.closest(".rating-star");
  if (!star || !state.pendingRatingMovieId) return;
  try {
    await submitRating(state.pendingRatingMovieId, star.dataset.score);
  } catch (error) {
    toast(error.message);
  }
});

$("#loginForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const mode = form.dataset.mode || "login";
  const payload = {
    username: form.username.value.trim(),
    password: form.password.value,
  };
  if (mode === "register") payload.email = form.email.value.trim();
  try {
    if (mode === "register") {
      const data = await api("/api/auth/register", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      if (data.token) localStorage.setItem(AUTH_TOKEN_KEY, data.token);
      state.user = data.user;
      state.admin = null;
      renderSession();
      closeLogin();
      showView("home");
      toast("注册成功");
      return;
    }

    const result = await loginWithAutoRole(payload);
    if (result.data.token) localStorage.setItem(AUTH_TOKEN_KEY, result.data.token);
    state.user = result.type === "user" ? result.data.user : null;
    state.admin = result.type === "admin" ? result.data.admin : null;
    renderSession();
    closeLogin();
    showView(result.type === "admin" ? "admin" : "home");
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

async function boot() {
  renderGallery(fallbackGalleryMovies);
  renderSession();
  await Promise.all([
    loadMe().catch((error) => toast(error.message)),
    loadCategories().catch((error) => toast(error.message)),
    loadGalleryMovies().catch((error) => toast(error.message)),
  ]);
}

boot().catch((error) => toast(error.message));
