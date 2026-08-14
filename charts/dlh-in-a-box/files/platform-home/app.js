const anonymousState = document.getElementById("anonymous-state");
const anonymousActions = document.getElementById("anonymous-actions");
const signedInContent = document.getElementById("signed-in-content");
const launchGroups = document.getElementById("launch-groups");
const emptyPanel = document.getElementById("empty-panel");
const loginButton = document.getElementById("login-button");
const sessionBar = document.getElementById("session-bar");
const sessionName = document.getElementById("session-name");
const logoutButton = document.getElementById("logout-button");
const administration = document.getElementById("administration");
const adminToolsPanel = document.getElementById("admin-tools-panel");
const adminTools = document.getElementById("admin-tools");
const portalNotice = document.getElementById("portal-notice");
const titleElement = document.getElementById("portal-title");
const subtitleElement = document.getElementById("portal-subtitle");
const portalLogo = document.getElementById("portal-logo");
const portalFavicon = document.getElementById("portal-favicon");
const portalThemeColor = document.getElementById("portal-theme-color");
const defaultLoginLabel = loginButton ? loginButton.textContent : "Sign in";
const routeNoticeStorageKey = "platform-home-route-notice";

const state = {
  config: null,
  keycloak: null,
  userRoles: [],
  isAdmin: false,
  health: {
    items: {},
    timer: null,
    lastUpdated: "",
  },
};

function show(element) {
  if (element) {
    element.classList.remove("is-hidden");
  }
}

function hide(element) {
  if (element) {
    element.classList.add("is-hidden");
  }
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function humanizeSlug(value) {
  return String(value || "")
    .split("-")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function buildPortalRedirectUri() {
  return `${window.location.origin}${window.location.pathname}`;
}

function expireCookie(name) {
  document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; Max-Age=0; path=/; SameSite=Lax`;
}

function currentLaunchTarget() {
  const segments = window.location.pathname
    .split("/")
    .filter(Boolean);
  if (segments.length === 2 && segments[0] === "launch") {
    return segments[1];
  }
  return "";
}

function rememberRouteNotice(level, message) {
  if (!message) {
    return;
  }
  try {
    window.sessionStorage.setItem(routeNoticeStorageKey, JSON.stringify({ level, message }));
  } catch (error) {
    console.warn("Unable to persist the route notice.", error);
  }
}

function consumeRouteNotice() {
  try {
    const raw = window.sessionStorage.getItem(routeNoticeStorageKey);
    window.sessionStorage.removeItem(routeNoticeStorageKey);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") {
      return null;
    }
    return {
      level: typeof parsed.level === "string" ? parsed.level : "info",
      message: typeof parsed.message === "string" ? parsed.message : "",
    };
  } catch (error) {
    return null;
  }
}

function clearTunnelOauthProxyCookies() {
  document.cookie
    .split(";")
    .map((entry) => entry.trim().split("=", 1)[0])
    .filter(Boolean)
    .filter((name) => name.startsWith("_oauth2_proxy"))
    .forEach((name) => expireCookie(name));
}

function groupItems(items, orderedGroups) {
  const buckets = new Map();
  items.forEach((item) => {
    const group = item.group || "Applications";
    if (!buckets.has(group)) {
      buckets.set(group, []);
    }
    buckets.get(group).push(item);
  });

  const ordered = [];
  orderedGroups.forEach((group) => {
    if (buckets.has(group)) {
      ordered.push([group, buckets.get(group)]);
      buckets.delete(group);
    }
  });

  Array.from(buckets.keys())
    .sort()
    .forEach((group) => ordered.push([group, buckets.get(group)]));

  return ordered;
}

function showHomeRoute() {
  show(launchGroups);
  if (!emptyPanel.classList.contains("is-hidden")) {
    show(emptyPanel);
  }
  if (state.isAdmin && administration) {
    show(administration);
  }
}

function setPortalNotice(level, message) {
  if (!portalNotice) {
    return;
  }
  if (!message) {
    portalNotice.textContent = "";
    portalNotice.className = "status-banner is-hidden";
    return;
  }
  portalNotice.innerHTML = message;
  portalNotice.className = `status-banner is-${level}`;
  show(portalNotice);
}

function renderCardIcon(item) {
  const iconStyle = item.iconBackground ? ` style="background: ${escapeHtml(item.iconBackground)}"` : "";
  if (item.iconUrl) {
    return `
      <div class="app-icon has-image"${iconStyle}>
        <img src="${escapeHtml(item.iconUrl)}" alt="${escapeHtml(item.iconAlt || `${item.name} logo`)}" loading="lazy" />
      </div>
    `;
  }
  const iconText = item.iconText || item.icon || item.name.slice(0, 2).toUpperCase();
  return `<div class="app-icon"${iconStyle} aria-hidden="true">${escapeHtml(iconText)}</div>`;
}

function healthLabel(status) {
  switch (String(status || "unknown")) {
    case "healthy":
      return "Healthy";
    case "degraded":
      return "Degraded";
    case "down":
      return "Down";
    default:
      return "Unknown";
  }
}

function healthStateFor(item) {
  if (!state.config?.health?.enabled) {
    return null;
  }
  return (
    state.health.items[item.id] || {
      status: "unknown",
      summary: "Waiting for the latest platform health check.",
      checkedAt: state.health.lastUpdated || "",
    }
  );
}

function formatHealthTimestamp(value) {
  if (!value) {
    return "";
  }
  const timestamp = new Date(value);
  if (Number.isNaN(timestamp.getTime())) {
    return "";
  }
  return timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function renderHealthStatus(item) {
  const health = healthStateFor(item);
  if (!health) {
    return "";
  }
  const checkedAt = formatHealthTimestamp(health.checkedAt);
  return `
    <div class="launch-card-meta">
      <span class="health-pill is-${escapeHtml(health.status || "unknown")}" title="${escapeHtml(health.summary || "")}">${escapeHtml(healthLabel(health.status))}</span>
      ${checkedAt ? `<span class="health-timestamp">Checked ${escapeHtml(checkedAt)}</span>` : ""}
    </div>
    <p class="health-summary">${escapeHtml(health.summary || "No health details available yet.")}</p>
  `;
}

function renderLaunchCard(item) {
  return `
    <article class="launch-card">
      <div class="launch-card-header">
        ${renderCardIcon(item)}
        <div class="launch-copy">
          <h3>${escapeHtml(item.name)}</h3>
          <p>${escapeHtml(item.summary || "")}</p>
        </div>
      </div>
      ${renderHealthStatus(item)}
      <a class="primary-button launch-button" href="${escapeHtml(item.url)}">Open</a>
    </article>
  `;
}

function renderGroupedCards(container, items, orderedGroups) {
  if (!container) {
    return;
  }
  container.innerHTML = groupItems(items, orderedGroups)
    .map(
      ([group, groupedItems]) => `
        <section class="panel panel-group">
          <div class="panel-header">
            <h2>${escapeHtml(group)}</h2>
          </div>
          <div class="launch-grid">
            ${groupedItems.map((item) => renderLaunchCard(item)).join("")}
          </div>
        </section>
      `,
    )
    .join("");
}

function setAnonymousState() {
  show(anonymousState);
  show(anonymousActions);
  hide(signedInContent);
  hide(sessionBar);
  hide(administration);
  hide(adminToolsPanel);
  setPortalNotice("", "");
}

function setLoginPending(label = "Starting sign-in...") {
  if (!loginButton) {
    return;
  }
  loginButton.disabled = true;
  loginButton.setAttribute("aria-busy", "true");
  loginButton.dataset.authReady = "false";
  loginButton.textContent = label;
}

function setLoginReady() {
  if (!loginButton) {
    return;
  }
  loginButton.disabled = false;
  loginButton.removeAttribute("aria-busy");
  loginButton.dataset.authReady = "true";
  loginButton.textContent = defaultLoginLabel;
}

function setAuthenticatedState(displayName, isAdmin) {
  hide(anonymousState);
  hide(anonymousActions);
  show(signedInContent);
  show(sessionBar);
  sessionName.textContent = displayName;
  if (isAdmin && administration) {
    show(administration);
  } else {
    hide(administration);
  }
}

function applyBranding(config) {
  const branding = config.branding || {};
  document.title = branding.title || "Data Platform";
  titleElement.textContent = branding.title || "Data Platform";
  if (branding.subtitle) {
    subtitleElement.textContent = branding.subtitle;
    show(subtitleElement);
  } else {
    subtitleElement.textContent = "";
    hide(subtitleElement);
  }

  if (branding.logoUrl) {
    portalLogo.src = branding.logoUrl;
    portalLogo.alt = branding.logoAlt || "Platform logo";
    show(portalLogo);
  } else {
    portalLogo.removeAttribute("src");
    hide(portalLogo);
  }

  if (portalFavicon) {
    if (branding.faviconUrl) {
      portalFavicon.href = branding.faviconUrl;
    } else {
      portalFavicon.removeAttribute("href");
    }
  }

  if (portalThemeColor && branding.metaThemeColor) {
    portalThemeColor.setAttribute("content", branding.metaThemeColor);
  }
}

function renderApps(config, userRoles) {
  if (!launchGroups) {
    return;
  }

  const visibleApps = (config.apps || []).filter((app) => {
    const requiredRoles = app.requiredRoles || [];
    return requiredRoles.length === 0 || requiredRoles.some((role) => userRoles.includes(role));
  });

  if (visibleApps.length === 0) {
    launchGroups.innerHTML = "";
    show(emptyPanel);
    return;
  }

  hide(emptyPanel);
  renderGroupedCards(launchGroups, visibleApps, ["Data Access", "Analysis", "Workflows"]);
}

function renderAdminTools(config, userRoles = []) {
  if (!adminToolsPanel || !adminTools) {
    return;
  }

  const tools = (config.admin?.tools || []).filter((tool) => {
    if (!tool.url) {
      return false;
    }
    const requiredRoles = tool.requiredRoles || [];
    return requiredRoles.length === 0 || requiredRoles.some((role) => userRoles.includes(role));
  });
  if (tools.length === 0) {
    hide(adminToolsPanel);
    hide(administration);
    return;
  }

  if (administration) {
    show(administration);
  }
  show(adminToolsPanel);
  renderGroupedCards(adminTools, tools, ["Governance & Access", "Platform Operations", "Cluster Operations"]);
}

async function apiRequest(path, options = {}) {
  if (!state.keycloak) {
    throw new Error("Authentication context is not ready.");
  }
  await state.keycloak.updateToken(60).catch(() => {
    throw new Error("Your session expired. Please sign in again.");
  });

  const headers = new Headers(options.headers || {});
  headers.set("Authorization", `Bearer ${state.keycloak.token}`);
  if (options.body !== undefined) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(path, {
    method: options.method || "GET",
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    credentials: "same-origin",
  });

  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();

  if (!response.ok) {
    const message =
      (payload && typeof payload === "object" && payload.error) ||
      (typeof payload === "string" && payload) ||
      `Request failed with status ${response.status}`;
    throw new Error(message);
  }

  return payload;
}

async function launchPortalTarget(target, options = {}) {
  if (!target) {
    return;
  }
  setPortalNotice("info", `Opening ${escapeHtml(humanizeSlug(target))}...`);
  const payload = await apiRequest(`/api/launch/${encodeURIComponent(target)}`);
  const targetUrl = String(payload?.url || "").trim();
  const launchMode = String(payload?.mode || "redirect").trim().toLowerCase();
  if (!targetUrl) {
    throw new Error(`The portal launcher for ${humanizeSlug(target)} did not return a URL.`);
  }

  if (launchMode === "popup") {
    const completeUrl = String(payload?.completeUrl || "").trim();
    const popup = window.open(
      targetUrl,
      `${target}-launcher`,
      "popup=yes,width=720,height=860,noopener=yes",
    );
    if (!popup) {
      if (!options.interactive) {
        throw new Error(`Your browser blocked the ${humanizeSlug(target)} sign-in window. Return to the portal and open it again from the launch card.`);
      }
      window.location.assign(targetUrl);
      return;
    }
    await new Promise((resolve, reject) => {
      const startedAt = Date.now();
      const timer = window.setInterval(() => {
        if (popup.closed) {
          window.clearInterval(timer);
          resolve();
          return;
        }
        if (Date.now() - startedAt > 120000) {
          window.clearInterval(timer);
          try {
            popup.close();
          } catch (error) {
            console.warn("Unable to close the launcher popup after timeout.", error);
          }
          reject(new Error(`${humanizeSlug(target)} sign-in did not finish before the launcher timed out.`));
        }
      }, 1000);
    });
    window.location.replace(completeUrl || targetUrl);
    return;
  }

  window.location.replace(targetUrl);
}

async function refreshHealth() {
  if (!state.config?.health?.enabled) {
    return;
  }
  try {
    const payload = await apiRequest("/api/health");
    const nextItems = {};
    (payload?.items || []).forEach((item) => {
      if (item && item.id) {
        nextItems[item.id] = item;
      }
    });
    state.health.items = nextItems;
    state.health.lastUpdated = payload?.checkedAt || new Date().toISOString();
  } catch (error) {
    console.warn("Unable to refresh portal health status.", error);
  }
  renderApps(state.config, state.userRoles);
  renderAdminTools(state.config, state.userRoles);
}

async function bootstrap() {
  clearTunnelOauthProxyCookies();
  setLoginPending();

  const response = await fetch("/config.json", { credentials: "same-origin" });
  if (!response.ok) {
    throw new Error(`Unable to load config.json: ${response.status}`);
  }

  state.config = await response.json();
  applyBranding(state.config);

  const keycloakModule = await import("/keycloak.js");
  const Keycloak = keycloakModule.default || keycloakModule.Keycloak;

  if (typeof Keycloak !== "function") {
    throw new Error("Keycloak browser adapter did not expose a constructor.");
  }

  const keycloak = new Keycloak({
    url: state.config.identity.keycloak.baseUrl,
    realm: state.config.identity.keycloak.realm,
    clientId: state.config.identity.keycloak.clientId,
  });
  state.keycloak = keycloak;

  const redirectUri = buildPortalRedirectUri();
  const authenticated = await keycloak.init({
    onLoad: "check-sso",
    pkceMethod: "S256",
    checkLoginIframe: false,
    redirectUri,
  });

  if (window.location.href !== redirectUri) {
    window.history.replaceState(null, document.title, redirectUri);
  }

  loginButton.addEventListener("click", () => {
    setLoginPending("Redirecting...");
    keycloak.login({ redirectUri });
  });

  if (!authenticated) {
    setLoginReady();
    setAnonymousState();
    return;
  }

  const claimName = state.config.identity.rolesClaim || "platform_roles";
  const rawRoles = keycloak.tokenParsed?.[claimName];
  state.userRoles = Array.isArray(rawRoles) ? rawRoles : typeof rawRoles === "string" && rawRoles ? [rawRoles] : [];
  const adminConfig = state.config.admin || {};
  const requiredRoles = adminConfig.requiredRoles || [];
  state.isAdmin = requiredRoles.length > 0 && requiredRoles.some((role) => state.userRoles.includes(role));
  const displayName =
    keycloak.tokenParsed?.name ||
    keycloak.tokenParsed?.preferred_username ||
    keycloak.tokenParsed?.email ||
    "Authenticated user";

  setAuthenticatedState(displayName, state.isAdmin);
  const routeNotice = consumeRouteNotice();
  if (routeNotice?.message) {
    setPortalNotice(routeNotice.level || "info", escapeHtml(routeNotice.message));
  } else {
    setPortalNotice("", "");
  }
  logoutButton.addEventListener("click", () => {
    keycloak.logout({ redirectUri: `${window.location.origin}/` });
  });
  document.addEventListener("click", (event) => {
    const launchLink = event.target.closest("a.launch-button[href^='/launch/']");
    if (!launchLink) {
      return;
    }
    const launchTarget = launchLink
      .getAttribute("href")
      .split("/")
      .filter(Boolean)[1] || "";
    if (!launchTarget) {
      return;
    }
    event.preventDefault();
    launchPortalTarget(launchTarget, { interactive: true }).catch((error) => {
      setPortalNotice("error", escapeHtml(error.message || `Unable to open ${humanizeSlug(launchTarget)}.`));
    });
  });

  window.setInterval(() => {
    keycloak.updateToken(60).catch(() => {
      keycloak.login({ redirectUri });
    });
  }, 30000);

  const launchTarget = currentLaunchTarget();
  if (launchTarget) {
    try {
      await launchPortalTarget(launchTarget);
    } catch (error) {
      rememberRouteNotice("error", error.message || `Unable to open ${humanizeSlug(launchTarget)} from the portal.`);
      window.location.assign("/");
    }
    return;
  }

  renderApps(state.config, state.userRoles);
  await refreshHealth();
  if (state.config?.health?.enabled && !state.health.timer) {
    const refreshIntervalSeconds = Number(state.config.health.refreshIntervalSeconds || 90);
    state.health.timer = window.setInterval(() => {
      refreshHealth().catch((error) => {
        console.warn("Periodic health refresh failed.", error);
      });
    }, Math.max(15, refreshIntervalSeconds) * 1000);
  }
  renderAdminTools(state.config, state.userRoles);
  showHomeRoute();
}

bootstrap().catch((error) => {
  setLoginReady();
  setAnonymousState();
  anonymousState.innerHTML = `
    <section class="panel panel-inline-status">
      <p class="panel-note">Sign-in is currently unavailable. Please try again in a moment.</p>
    </section>
  `;
  console.error(error);
});
