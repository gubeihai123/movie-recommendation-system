// GitHub Pages 前端配置：部署 Render 后端后，把这里改成你的后端公网地址。
window.MOVIE_API_BASE = "https://movie-recommendation-system-68a3.onrender.com";

(() => {
  const API = window.MOVIE_API_BASE;
  const AUTH_TOKEN_KEY = "movie_recsys_auth_token";
  const movies = [
    [1, "阿甘正传", "/static/posters/movie_001.jpg"],
    [2, "教父", "/static/posters/movie_002.jpg"],
    [4, "黑客帝国", "/static/posters/movie_004.png"],
    [7, "千与千寻", "/static/posters/movie_007.png"],
    [9, "低俗小说", "/static/posters/movie_009.jpg"],
    [14, "盗梦空间", "/static/posters/movie_014.jpg"],
    [17, "机器人总动员", "/static/posters/movie_017.jpg"],
    [27, "星际穿越", "/static/posters/movie_027.jpg"],
    [36, "寻梦环游记", "/static/posters/movie_036.jpg"],
    [77, "龙猫", "/static/posters/movie_077.jpg"]
  ];
  const $ = (selector) => document.querySelector(selector);
  const poster = (url) => {
    if (/^https?:\/\//i.test(url)) return url;
    if (url.startsWith("/static/posters/")) {
      return new URL(url.slice(1), document.baseURI).href;
    }
    return `${API}${url}`;
  };

  function setHidden(selector, hidden) {
    const el = $(selector);
    if (el) el.hidden = hidden;
  }

  function renderTokenSession() {
    const loggedIn = Boolean(localStorage.getItem(AUTH_TOKEN_KEY));
    setHidden("#openLoginBtn", loggedIn);
    setHidden("#openRegisterBtn", loggedIn);
    setHidden("#logoutBtn", !loggedIn);
    setHidden("#heroRecommendBtn", !loggedIn);
  }

  const nativeFetch = window.fetch.bind(window);
  window.fetch = (input, init = {}) => {
    const url = typeof input === "string" ? input : input?.url || "";
    let absoluteUrl = /^https?:\/\//i.test(url) ? url : `${API}${url.startsWith("/") ? url : `/${url}`}`;
    if (absoluteUrl.startsWith(API) && absoluteUrl.includes("/api/movies")) {
      const cappedUrl = new URL(absoluteUrl);
      const pageSize = Number(cappedUrl.searchParams.get("page_size") || 0);
      if (pageSize > 40) cappedUrl.searchParams.set("page_size", "36");
      absoluteUrl = cappedUrl.toString();
      input = absoluteUrl;
    }
    const token = localStorage.getItem(AUTH_TOKEN_KEY);
    if (!absoluteUrl.startsWith(API) || !token) return nativeFetch(input, init);

    const headers = new Headers(init.headers || {});
    if (!headers.has("Authorization")) headers.set("Authorization", `Bearer ${token}`);
    return nativeFetch(input, { ...init, headers }).then((response) => {
      if (absoluteUrl.includes("/api/auth/logout")) {
        localStorage.removeItem(AUTH_TOKEN_KEY);
        renderTokenSession();
      }
      return response;
    });
  };

  function transform(index, total) {
    const angle = (index / total) * Math.PI * 2;
    const x = Math.cos(angle) * 320;
    const z = Math.sin(angle) * 320;
    const y = ((index % 5) - 2) * 72;
    const ry = angle * 180 / Math.PI + 90;
    return `translate(-50%, -50%) translate3d(${x}px, ${y}px, ${z}px) rotateY(${ry}deg) scale(1)`;
  }

  function drawFallbackSphere() {
    const holder = $("#movieSphere");
    if (!holder || holder.children.length) return;
    holder.innerHTML = movies.slice(0, 6).map((movie, index) => `
      <button class="sphere-card" type="button" data-gallery-id="${movie[0]}"
        style="--sphere-transform:${transform(index, movies.length)}; --arc-transform:${transform(index, movies.length)}">
        <img src="${poster(movie[2])}" alt="${movie[1]}" loading="${index < 3 ? "eager" : "lazy"}" decoding="async">
      </button>
    `).join("");
  }

  function openAuth(register = false) {
    const modal = $("#loginModal");
    const form = $("#loginForm");
    if (!modal || !form) return;
    form.dataset.mode = register ? "register" : "login";
    $("#loginTitle").textContent = register ? "用户注册" : "账号登录";
    $("#emailField").hidden = !register;
    $("#registerRules").hidden = !register;
    $("#authSubmitBtn").textContent = register ? "注册并登录" : "登录";
    $("#toggleAuthModeBtn").textContent = register ? "已有账号？返回登录" : "还没有账号？立即注册";
    modal.classList.add("open");
    modal.setAttribute("aria-hidden", "false");
  }

  function showHome() {
    document.querySelectorAll("[data-view-panel]").forEach((panel) => {
      panel.classList.toggle("active", panel.dataset.viewPanel === "home");
    });
    if ($("#homeNavBtn")) $("#homeNavBtn").hidden = true;
    if ($("#heroRecommendBtn")) $("#heroRecommendBtn").hidden = false;
  }

  async function requestJson(path, payload) {
    const response = await fetch(`${API}${path}`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.message || "请求失败");
    return data;
  }

  async function submitAuth(event) {
    const form = event.target;
    if (!form || form.id !== "loginForm") return;
    event.preventDefault();
    event.stopImmediatePropagation();

    const mode = form.dataset.mode || "login";
    const payload = {
      username: form.username.value.trim(),
      password: form.password.value,
    };
    if (mode === "register") payload.email = form.email.value.trim();

    const message = $("#loginMessage");
    const button = $("#authSubmitBtn");
    if (message) message.textContent = mode === "register" ? "正在注册..." : "正在登录...";
    if (button) button.disabled = true;

    try {
      if (mode === "register") {
        const data = await requestJson("/api/auth/register", payload);
        if (data.token) localStorage.setItem(AUTH_TOKEN_KEY, data.token);
      } else {
        try {
          const data = await requestJson("/api/auth/login", payload);
          if (data.token) localStorage.setItem(AUTH_TOKEN_KEY, data.token);
        } catch (userError) {
          const data = await requestJson("/api/auth/admin/login", payload);
          if (data.token) localStorage.setItem(AUTH_TOKEN_KEY, data.token);
        }
      }
      if (message) message.textContent = "登录成功，正在刷新页面...";
      renderTokenSession();
      window.setTimeout(() => {
        const url = new URL(window.location.href);
        url.searchParams.set("v", Date.now().toString());
        window.location.replace(url.toString());
      }, 250);
    } catch (error) {
      if (message) message.textContent = error.message || "登录失败";
      if (button) button.disabled = false;
    }
  }

  drawFallbackSphere();
  renderTokenSession();
  $("#openLoginBtn")?.addEventListener("click", () => openAuth(false));
  $("#openRegisterBtn")?.addEventListener("click", () => openAuth(true));
  $("#toggleAuthModeBtn")?.addEventListener("click", () => openAuth($("#loginForm")?.dataset.mode !== "register"));
  $("#closeLoginBtn")?.addEventListener("click", () => $("#loginModal")?.classList.remove("open"));
  $("#homeNavBtn")?.addEventListener("click", showHome);
  document.addEventListener("submit", submitAuth, true);
})();
