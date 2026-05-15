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
const roleManagementPanel = document.getElementById("role-management-panel");
const roleManagementStatus = document.getElementById("role-management-status");
const portalNotice = document.getElementById("portal-notice");
const roleCatalog = document.getElementById("role-catalog");
const roleDetail = document.getElementById("role-detail");
const accessControlBack = document.getElementById("access-control-back");
const titleElement = document.getElementById("portal-title");
const subtitleElement = document.getElementById("portal-subtitle");
const portalLogo = document.getElementById("portal-logo");
const portalFavicon = document.getElementById("portal-favicon");
const portalThemeColor = document.getElementById("portal-theme-color");
const defaultLoginLabel = loginButton ? loginButton.textContent : "Sign in";
const sectionStorageKey = "platform-home-target-section";
const routeNoticeStorageKey = "platform-home-route-notice";
const accessControlPath = "/access-control";

const state = {
  config: null,
  keycloak: null,
  groups: [],
  isAdmin: false,
  adminStatus: null,
  roles: [],
  selectedRoleKey: null,
  activeRoleTab: "overview",
  search: {
    user: { query: "", results: [], loading: false, error: "" },
    exception: { query: "", results: [], loading: false, error: "" },
    group: { query: "", results: [], loading: false, error: "" },
  },
  exceptionDraft: {
    mode: "create",
    exceptionId: "",
    username: "",
    displayName: "",
    email: "",
    reason: "",
    approvalRef: "",
    expiresAt: "",
  },
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

function emptyExceptionDraft() {
  return {
    mode: "create",
    exceptionId: "",
    username: "",
    displayName: "",
    email: "",
    reason: "",
    approvalRef: "",
    expiresAt: "",
  };
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
  const path = window.location.pathname === "/admin.html" ? "/" : window.location.pathname;
  return `${window.location.origin}${path}`;
}

function expireCookie(name) {
  document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; Max-Age=0; path=/; SameSite=Lax`;
}

function rememberTargetSection(section) {
  if (!section) {
    return;
  }
  try {
    window.sessionStorage.setItem(sectionStorageKey, section);
  } catch (error) {
    console.warn("Unable to persist the requested portal section.", error);
  }
}

function currentPortalRoute() {
  return window.location.pathname === accessControlPath ? "access-control" : "home";
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

function getTargetSection() {
  if (window.location.hash === "#administration" || window.location.pathname === accessControlPath) {
    return "access-control";
  }
  try {
    return window.sessionStorage.getItem(sectionStorageKey) || "";
  } catch (error) {
    return "";
  }
}

function clearTargetSection() {
  try {
    window.sessionStorage.removeItem(sectionStorageKey);
  } catch (error) {
    console.warn("Unable to clear the requested portal section.", error);
  }
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
  hide(roleManagementPanel);
  hide(accessControlBack);
}

function showAccessControlRoute() {
  hide(launchGroups);
  hide(emptyPanel);
  hide(administration);
  show(roleManagementPanel);
  show(accessControlBack);
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

function accessControlEnabled() {
  return Boolean(state.config?.admin?.accessControlEnabled);
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
  hide(roleManagementPanel);
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
  hide(roleManagementPanel);
  if (isAdmin && administration && currentPortalRoute() !== "access-control") {
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

function renderApps(config, groups) {
  if (!launchGroups) {
    return;
  }

  const visibleApps = (config.apps || []).filter((app) => {
    const requiredGroups = app.requiredGroups || [];
    return requiredGroups.length === 0 || requiredGroups.some((group) => groups.includes(group));
  });

  if (visibleApps.length === 0) {
    launchGroups.innerHTML = "";
    show(emptyPanel);
    return;
  }

  hide(emptyPanel);
  renderGroupedCards(launchGroups, visibleApps, ["Data Access", "Analysis", "Workflows"]);
}

function renderAdminTools(config, isAdmin) {
  if (!adminToolsPanel || !adminTools) {
    return;
  }

  if (!isAdmin || currentPortalRoute() === "access-control") {
    hide(adminToolsPanel);
    return;
  }

  const tools = (config.admin?.tools || []).filter((tool) => tool.url);
  if (tools.length === 0) {
    hide(adminToolsPanel);
    return;
  }

  show(adminToolsPanel);
  renderGroupedCards(adminTools, tools, ["Governance & Access", "Platform Operations", "Cluster Operations"]);
}

function setRoleManagementMessage(level, message) {
  if (!roleManagementStatus) {
    return;
  }
  if (!message) {
    roleManagementStatus.textContent = "";
    roleManagementStatus.className = "status-banner is-hidden";
    return;
  }
  roleManagementStatus.innerHTML = message;
  roleManagementStatus.className = `status-banner is-${level}`;
  show(roleManagementStatus);
}

function currentRole() {
  if (state.roles.length === 0) {
    return null;
  }
  return (
    state.roles.find((role) => role.key === state.selectedRoleKey) ||
    state.roles[0] ||
    null
  );
}

function memberKindLabel(kind) {
  return kind === "group" ? "Group" : "User";
}

function canEditUserMembers() {
  return Boolean(
    state.adminStatus &&
      state.adminStatus.membershipSource === "ranger" &&
      state.adminStatus.ldapReachable,
  );
}

function canEditUsers() {
  return canEditUserMembers() && Boolean(state.adminStatus && state.adminStatus.exceptionSupportEnabled);
}

function canEditGroups() {
  return canEditUserMembers() && Boolean(state.adminStatus && state.adminStatus.groupAssignmentEnabled);
}

function isAssigned(role, kind, name) {
  const members =
    kind === "group"
      ? role.members.groups
      : role.members.users;
  return members.includes(name);
}

function renderMemberList(kind, role, members, emptyText, editable) {
  if (!members || members.length === 0) {
    return `<span class="detail-empty">${escapeHtml(emptyText)}</span>`;
  }

  return members
    .map(
      (name) => `
        <span class="member-chip">
          <span class="member-kind">${escapeHtml(memberKindLabel(kind))}</span>
          <span class="member-name">${escapeHtml(name)}</span>
          ${
            editable
              ? `<button type="button" class="member-remove" data-action="remove-member" data-kind="${escapeHtml(kind)}" data-name="${escapeHtml(name)}" data-role-key="${escapeHtml(role.key)}">Remove</button>`
              : ""
          }
        </span>
      `,
    )
    .join("");
}

function renderSearchResults(kind, role) {
  const search = state.search[kind];
  const isExceptionSearch = kind === "exception";
  const searchKind = isExceptionSearch ? "user" : kind;
  const editable = searchKind === "group" ? canEditGroups() : (isExceptionSearch ? canEditUsers() : canEditUserMembers());
  if (!editable) {
    return `<p class="detail-empty">${
      searchKind === "group"
        ? "Directory-group assignment is unavailable until LDAP and Ranger usersync are enabled."
        : isExceptionSearch
          ? "Direct-user exceptions are unavailable while live access-control editing is disabled."
          : "Direct-user role membership is unavailable while live access-control editing is disabled."
    }</p>`;
  }
  if (search.loading) {
    return `<p class="detail-empty">Searching LDAP-backed ${searchKind === "group" ? "groups" : "users"}...</p>`;
  }
  if (search.error) {
    return `<p class="detail-empty">${escapeHtml(search.error)}</p>`;
  }
  if (!search.query.trim()) {
    return `<p class="detail-empty">Search the organizational directory for ${searchKind === "group" ? "groups" : "users"} to assign to this platform role.</p>`;
  }
  if (search.results.length === 0) {
    return `<p class="detail-empty">No matching directory ${searchKind === "group" ? "groups" : "users"} found.</p>`;
  }
  return search.results
    .map((result) => {
      const name = result.name || "";
      const displayName = result.displayName || name;
      const assigned = isAssigned(role, searchKind, name);
      const metadata = [];
      if (searchKind === "user" && result.email) {
        metadata.push(result.email);
      }
      if (displayName !== name) {
        metadata.unshift(name);
      }
      return `
        <div class="search-result-row">
          <div class="search-result-copy">
            <span class="member-kind">${escapeHtml(memberKindLabel(searchKind))}</span>
            <strong>${escapeHtml(displayName)}</strong>
            ${metadata.length ? `<span>${escapeHtml(metadata.join(" • "))}</span>` : ""}
          </div>
          <button
            type="button"
            class="secondary-button compact-button"
            data-action="${searchKind === "group" ? "add-member" : isExceptionSearch ? "select-exception-user" : "add-member"}"
            data-kind="${escapeHtml(searchKind)}"
            data-name="${escapeHtml(name)}"
            data-display-name="${escapeHtml(displayName)}"
            data-email="${escapeHtml(result.email || "")}"
            data-role-key="${escapeHtml(role.key)}"
            ${assigned ? "disabled" : ""}
          >
            ${assigned ? "Assigned" : searchKind === "group" ? "Add" : isExceptionSearch ? "Use" : "Add"}
          </button>
        </div>
      `;
    })
    .join("");
}

function formatDateLabel(value) {
  if (!value) {
    return "";
  }
  const timestamp = new Date(value);
  if (Number.isNaN(timestamp.getTime())) {
    return value;
  }
  return timestamp.toLocaleDateString();
}

function normalizeDateInputValue(value) {
  if (!value) {
    return "";
  }
  const timestamp = new Date(value);
  if (Number.isNaN(timestamp.getTime())) {
    return "";
  }
  return timestamp.toISOString().slice(0, 10);
}

function renderRoleCatalog() {
  if (!roleCatalog) {
    return;
  }

  if (state.roles.length === 0) {
    roleCatalog.innerHTML = `
      <div class="panel-subtle">
        <p class="panel-note">No manageable platform roles are available for administration.</p>
      </div>
    `;
    return;
  }

  roleCatalog.innerHTML = state.roles
    .map((role) => {
      const selected = currentRole() && currentRole().key === role.key;
      const membershipCount =
        (role.members?.users?.length || 0) +
        (role.members?.groups?.length || 0) +
        (role.exceptions?.active?.length || 0);
      const displayName = role.displayName || humanizeSlug(role.key);
      return `
        <button type="button" class="role-catalog-item ${selected ? "is-active" : ""}" data-action="select-role" data-role-key="${escapeHtml(role.key)}">
          <span class="role-catalog-copy">
            <strong>${escapeHtml(displayName)}</strong>
            <span>${escapeHtml(role.description || "Git-defined platform role")}</span>
          </span>
          <span class="badge">${membershipCount}</span>
        </button>
      `;
    })
    .join("");
}

function renderRoleDetail() {
  if (!roleDetail) {
    return;
  }

  const role = currentRole();
  if (!role) {
    roleDetail.innerHTML = `<p class="panel-note">Select a platform role to review live membership, assign LDAP users or groups, and inspect policy impact.</p>`;
    return;
  }

  const groupSearchDisabled = !canEditGroups();
  const userSearchDisabled = !canEditUserMembers();
  const exceptionSearchDisabled = !canEditUsers();
  const displayName = role.displayName || humanizeSlug(role.key);
  const auditLink =
    state.adminStatus && state.adminStatus.auditUrl
      ? `<a href="${escapeHtml(state.adminStatus.auditUrl)}" target="_blank" rel="noreferrer">Open Ranger Admin</a>`
      : "Ranger Admin";
  const activeExceptions = role.exceptions?.active || [];
  const declaredExceptions = role.exceptions?.declared || [];
  const appEntitlements = Object.entries(role.apps || {})
    .filter(([, enabled]) => Boolean(enabled))
    .map(([name]) => humanizeSlug(name.replace(/Ui$/, "-ui")));
  const policySummaries = role.policySummaries || [];
  const activeTab = state.activeRoleTab || "overview";
  const hasDraft = Boolean(state.exceptionDraft.username);

  const overviewPanel = `
    <section class="detail-stack">
      <div class="detail-row role-metadata-row">
        <span class="detail-chip">Ranger role: ${escapeHtml(role.name || role.key)}</span>
        <span class="detail-chip">Nested roles: ${escapeHtml(role.nestedRoles && role.nestedRoles.length ? role.nestedRoles.join(", ") : "None")}</span>
      </div>
      <div class="detail-row role-metadata-row">
        <span class="detail-chip">Approved users: ${escapeHtml(String(role.members.users.length))}</span>
        <span class="detail-chip">LDAP groups: ${escapeHtml(String(role.members.groups.length))}</span>
        <span class="detail-chip">Active exceptions: ${escapeHtml(String(activeExceptions.length))}</span>
      </div>
      <section class="admin-section">
        <h4>Current direct-user members</h4>
        <div class="member-list">
          ${renderMemberList("user", role, role.members.users, "No direct users assigned", canEditUserMembers())}
        </div>
      </section>
      <section class="admin-section">
        <h4>Application entitlements</h4>
        ${
          appEntitlements.length
            ? `<div class="member-list">${appEntitlements
                .map((name) => `<span class="detail-chip">${escapeHtml(name)}</span>`)
                .join("")}</div>`
            : `<p class="detail-empty">This role does not expose browser entitlements.</p>`
        }
      </section>
      <section class="admin-section">
        <h4>Linked Ranger policies</h4>
        ${
          policySummaries.length
            ? `<div class="policy-summary-list">${policySummaries
                .map(
                  (policy) => `
                    <article class="policy-summary">
                      <strong>${escapeHtml(policy.name || "Unnamed policy")}</strong>
                      <span>${escapeHtml(policy.kind || "access")}</span>
                      <p>${escapeHtml(policy.description || "No description provided.")}</p>
                    </article>
                  `,
                )
                .join("")}</div>`
            : `<p class="detail-empty">No Ranger bootstrap policies currently target this role.</p>`
        }
      </section>
    </section>
  `;

  const groupPanel = `
    <section class="admin-section">
      <div class="membership-header">
        <h4>Directory groups</h4>
        <span class="badge">${escapeHtml(String(role.members.groups.length))}</span>
      </div>
      <div class="member-list">
        ${renderMemberList("group", role, role.members.groups, "No LDAP groups assigned", canEditGroups())}
      </div>
      <form class="principal-search-form" data-kind="group">
        <label class="search-label" for="group-principal-query">Add LDAP group</label>
        <div class="search-input-row">
          <input id="group-principal-query" class="search-input" name="query" type="search" value="${escapeHtml(state.search.group.query)}" placeholder="Search LDAP groups" ${groupSearchDisabled ? "disabled" : ""} />
          <button type="submit" class="secondary-button compact-button" ${groupSearchDisabled ? "disabled" : ""}>Search</button>
        </div>
      </form>
      <div class="search-results">
        ${renderSearchResults("group", role)}
      </div>
    </section>
  `;

  const userPanel = `
    <section class="admin-section">
      <div class="membership-header">
        <h4>Directory users</h4>
        <span class="badge">${escapeHtml(String(role.members.users.length))}</span>
      </div>
      <div class="member-list">
        ${renderMemberList("user", role, role.members.users, "No direct users assigned", canEditUserMembers())}
      </div>
      <form class="principal-search-form" data-kind="user">
        <label class="search-label" for="role-user-query">Add LDAP user</label>
        <div class="search-input-row">
          <input id="role-user-query" class="search-input" name="query" type="search" value="${escapeHtml(state.search.user.query)}" placeholder="Search LDAP users" ${userSearchDisabled ? "disabled" : ""} />
          <button type="submit" class="secondary-button compact-button" ${userSearchDisabled ? "disabled" : ""}>Search</button>
        </div>
      </form>
      <div class="search-results">
        ${renderSearchResults("user", role)}
      </div>
    </section>
  `;

  const editableExceptions = canEditUsers();
  const draftMode = state.exceptionDraft.mode === "edit" ? "edit" : "create";
  const isEditingException = draftMode === "edit" && Boolean(state.exceptionDraft.exceptionId);

  const activeExceptionHtml = activeExceptions.length
    ? activeExceptions
        .map(
          (exception) => `
            <article class="exception-card">
              <div class="search-result-copy">
                <span class="member-kind">User exception</span>
                <strong>${escapeHtml(exception.displayName || exception.username)}</strong>
                <span>${escapeHtml([exception.username, exception.email].filter(Boolean).join(" • "))}</span>
              </div>
              <p>${escapeHtml(exception.reason || "No reason recorded.")}</p>
              <p class="detail-note">Approval ${escapeHtml(exception.approvalRef || "n/a")} • Expires ${escapeHtml(formatDateLabel(exception.expiresAt))}</p>
              ${
                editableExceptions
                  ? `
                    <div class="detail-row role-metadata-row">
                      <button type="button" class="secondary-button compact-button" data-action="edit-exception" data-role-key="${escapeHtml(role.key)}" data-exception-id="${escapeHtml(exception.id)}" data-name="${escapeHtml(exception.username || "")}" data-display-name="${escapeHtml(exception.displayName || exception.username || "")}" data-email="${escapeHtml(exception.email || "")}" data-reason="${escapeHtml(exception.reason || "")}" data-approval-ref="${escapeHtml(exception.approvalRef || "")}" data-expires-at="${escapeHtml(normalizeDateInputValue(exception.expiresAt) || "")}">Edit</button>
                      <button type="button" class="secondary-button compact-button" data-action="remove-exception" data-role-key="${escapeHtml(role.key)}" data-exception-id="${escapeHtml(exception.id)}">Remove</button>
                    </div>
                  `
                  : ""
              }
            </article>
          `,
        )
        .join("")
    : `<p class="detail-empty">No active direct-user exceptions are recorded for this role.</p>`;

  const declaredExceptionHtml = declaredExceptions.length
    ? `<div class="declared-exception-list">${declaredExceptions
        .map(
          (exception) => `
            <article class="policy-summary">
              <strong>${escapeHtml(exception.username || "Declared exception")}</strong>
              <span>${escapeHtml(exception.approvalRef || "Git-managed")}</span>
              <p>${escapeHtml(exception.reason || "Declared in values and managed through Git.")}</p>
            </article>
          `,
        )
        .join("")}</div>`
    : `<p class="detail-empty">No Git-managed declared exceptions are defined for this role.</p>`;

  const exceptionPanel = `
    <section class="detail-stack">
      <section class="admin-section">
        <div class="membership-header">
          <h4>Active direct-user exceptions</h4>
          <span class="badge">${escapeHtml(String(activeExceptions.length))}</span>
        </div>
        ${activeExceptionHtml}
      </section>
      <section class="admin-section">
        <h4>Git-managed declared exceptions</h4>
        ${declaredExceptionHtml}
      </section>
      <section class="admin-section">
        <h4>${isEditingException ? "Update direct-user exception" : "Create direct-user exception"}</h4>
        <p class="detail-note">${
          isEditingException
            ? "Update the reason, approval reference, or expiry for this active exception."
            : "Use direct users only for time-bounded exceptions. Durable access should be assigned through LDAP groups."
        }</p>
        ${
          isEditingException
            ? ""
            : `
              <form class="principal-search-form" data-kind="exception">
                <label class="search-label" for="user-principal-query">Search LDAP user</label>
                <div class="search-input-row">
                  <input id="user-principal-query" class="search-input" name="query" type="search" value="${escapeHtml(state.search.exception.query)}" placeholder="Search LDAP users" ${exceptionSearchDisabled ? "disabled" : ""} />
                  <button type="submit" class="secondary-button compact-button" ${exceptionSearchDisabled ? "disabled" : ""}>Search</button>
                </div>
              </form>
              <div class="search-results">
                ${renderSearchResults("exception", role)}
              </div>
            `
        }
        ${
          hasDraft
            ? `
              <form class="exception-form" data-role-key="${escapeHtml(role.key)}">
                <div class="detail-row role-metadata-row">
                  <span class="detail-chip">Selected user: ${escapeHtml(state.exceptionDraft.displayName || state.exceptionDraft.username)}</span>
                  <button type="button" class="secondary-button compact-button" data-action="clear-exception-draft">${isEditingException ? "Cancel edit" : "Clear"}</button>
                </div>
                <label class="search-label" for="exception-reason">Reason</label>
                <textarea id="exception-reason" class="search-input search-input-multiline" name="reason" required>${escapeHtml(state.exceptionDraft.reason)}</textarea>
                <label class="search-label" for="exception-approval-ref">Approval reference</label>
                <input id="exception-approval-ref" class="search-input" name="approvalRef" type="text" value="${escapeHtml(state.exceptionDraft.approvalRef)}" required />
                <label class="search-label" for="exception-expires-at">Expires at</label>
                <input id="exception-expires-at" class="search-input" name="expiresAt" type="date" value="${escapeHtml(state.exceptionDraft.expiresAt)}" required />
                <button type="submit" class="primary-button launch-button">${isEditingException ? "Update exception" : "Create exception"}</button>
              </form>
            `
            : `<p class="detail-empty">${isEditingException ? "Choose an active exception above to edit it." : "Select an LDAP user above, then provide a reason, approval reference, and expiry date."}</p>`
        }
      </section>
    </section>
  `;

  const panelContent =
    activeTab === "groups"
      ? groupPanel
      : activeTab === "users"
        ? userPanel
      : activeTab === "exceptions"
        ? exceptionPanel
        : overviewPanel;

  roleDetail.innerHTML = `
    <article class="role-editor">
      <div class="admin-card-header">
        <div>
          <p class="eyebrow eyebrow-tight">Platform role</p>
          <h3>${escapeHtml(displayName)}</h3>
          <p class="detail-note">${escapeHtml(role.description || "Platform role catalog entry.")}</p>
        </div>
        <span class="badge">${escapeHtml(role.name || role.key)}</span>
      </div>
      <p class="detail-note role-editor-note">Role definitions and seeded defaults stay Git-managed. Routine membership changes happen here and persist in Ranger. Use ${auditLink} for deeper policy audit and troubleshooting.</p>
      <div class="role-tab-strip">
        <button type="button" class="tab-button ${activeTab === "overview" ? "is-active" : ""}" data-action="select-role-tab" data-tab="overview">Overview</button>
        <button type="button" class="tab-button ${activeTab === "users" ? "is-active" : ""}" data-action="select-role-tab" data-tab="users">Directory Users</button>
        <button type="button" class="tab-button ${activeTab === "groups" ? "is-active" : ""}" data-action="select-role-tab" data-tab="groups">Directory Groups</button>
        <button type="button" class="tab-button ${activeTab === "exceptions" ? "is-active" : ""}" data-action="select-role-tab" data-tab="exceptions">Direct User Exceptions</button>
      </div>
      ${panelContent}
    </article>
  `;

  roleDetail.querySelectorAll("[data-action='add-member'], [data-action='remove-member'], [data-action='select-exception-user'], [data-action='clear-exception-draft'], [data-action='edit-exception'], [data-action='remove-exception'], [data-action='select-role-tab']").forEach((element) => {
    element.addEventListener("click", handleRoleAction);
  });
  roleDetail.querySelectorAll(".principal-search-form").forEach((form) => {
    form.addEventListener("submit", handlePrincipalSearch);
  });
  roleDetail.querySelectorAll(".exception-form").forEach((form) => {
    form.addEventListener("submit", handleExceptionSubmit);
  });
}

function renderRoleManagement() {
  if (!roleManagementPanel) {
    return;
  }

  if (!state.isAdmin || !state.config?.admin?.roleManagementEnabled) {
    hide(roleManagementPanel);
    return;
  }

  if (currentPortalRoute() === "access-control") {
    showAccessControlRoute();
  } else {
    showHomeRoute();
    return;
  }

  renderRoleCatalog();
  renderRoleDetail();

  if (!state.adminStatus) {
    setRoleManagementMessage("info", "Loading live access-control status...");
    return;
  }

  const rangerAdminLink =
    state.adminStatus.auditUrl
      ? `<a href="${escapeHtml(state.adminStatus.auditUrl)}" target="_blank" rel="noreferrer">Ranger Admin</a>`
      : "Ranger Admin";

  if (state.adminStatus.membershipSource !== "ranger") {
    setRoleManagementMessage(
      "warning",
      `Live access-control edits are disabled because Keycloak owns platform role membership. Current source: <code>${escapeHtml(state.adminStatus.membershipSource)}</code>. Use Keycloak Admin for routine role changes.`,
    );
    return;
  }

  if (!state.adminStatus.ldapReachable) {
    setRoleManagementMessage(
      "warning",
      `LDAP-backed discovery is currently unavailable, so new assignments are read-only. Existing Ranger memberships remain visible. Use ${rangerAdminLink} for audit context while directory connectivity is restored.`,
    );
    return;
  }

  if (!state.adminStatus.groupAssignmentEnabled) {
    setRoleManagementMessage(
      "info",
      `LDAP group discovery is active, but group assignment remains disabled until Ranger usersync is healthy. Direct-user exceptions remain available for approved break-glass cases.`,
    );
    return;
  }

  setRoleManagementMessage(
    "success",
    `LDAP-backed access-control management is enabled. Durable access should use groups; direct users remain governed exceptions. Use ${rangerAdminLink} for deeper audit context.`,
  );
}

function attachRoleCatalogHandlers() {
  if (!roleCatalog) {
    return;
  }
  roleCatalog.querySelectorAll("[data-action='select-role']").forEach((element) => {
    element.addEventListener("click", handleRoleAction);
  });
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

async function refreshRoleData() {
  const [statusPayload, rolesPayload] = await Promise.all([
    apiRequest("/api/admin/access-control/status"),
    apiRequest("/api/admin/access-control/roles"),
  ]);
  state.adminStatus = statusPayload || {};
  state.roles = (Array.isArray(rolesPayload?.roles) ? rolesPayload.roles : []).filter((role) => role.manageable !== false);
  if (!state.roles.some((role) => role.key === state.selectedRoleKey)) {
    state.selectedRoleKey = state.roles.length > 0 ? state.roles[0].key : null;
  }
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
  renderApps(state.config, state.groups);
  renderAdminTools(state.config, state.isAdmin);
}

async function handlePrincipalSearch(event) {
  event.preventDefault();
  const kind = event.currentTarget.dataset.kind;
  const searchKind = kind === "exception" ? "exception" : kind;
  const endpointKind = kind === "group" ? "group" : "user";
  const formData = new FormData(event.currentTarget);
  const query = String(formData.get("query") || "").trim();
  state.search[searchKind] = { query, results: [], loading: false, error: "" };

  if (query.length < 2) {
    state.search[searchKind].error = "Enter at least two characters to search the directory.";
    renderRoleDetail();
    return;
  }

  state.search[searchKind].loading = true;
  renderRoleDetail();
  try {
    const endpoint =
      endpointKind === "group"
        ? `/api/admin/access-control/directory-groups?query=${encodeURIComponent(query)}`
        : `/api/admin/access-control/directory-users?query=${encodeURIComponent(query)}`;
    const payload = await apiRequest(endpoint);
    state.search[searchKind] = {
      query,
      results: Array.isArray(payload?.results) ? payload.results : [],
      loading: false,
      error: "",
    };
  } catch (error) {
    state.search[searchKind] = { query, results: [], loading: false, error: error.message };
  }
  renderRoleDetail();
}

async function mutateRoleMembership(method, roleKey, kind, name) {
  const actionLabel = method === "DELETE" ? "Removing membership..." : "Adding membership...";
  setRoleManagementMessage("info", actionLabel);
  const endpoint =
    kind === "group"
      ? `/api/admin/access-control/roles/${encodeURIComponent(roleKey)}/groups`
      : `/api/admin/access-control/roles/${encodeURIComponent(roleKey)}/users`;
  await apiRequest(endpoint, {
    method,
    body: { kind, name },
  });
  await refreshRoleData();
  state.search[kind] = { query: "", results: [], loading: false, error: "" };
  renderRoleManagement();
}

async function handleExceptionSubmit(event) {
  event.preventDefault();
  const role = currentRole();
  if (!role || !state.exceptionDraft.username) {
    setRoleManagementMessage("error", "Choose an LDAP user before saving an exception.");
    return;
  }
  const formData = new FormData(event.currentTarget);
  const payload = {
    username: state.exceptionDraft.username,
    displayName: state.exceptionDraft.displayName,
    email: state.exceptionDraft.email,
    reason: String(formData.get("reason") || "").trim(),
    approvalRef: String(formData.get("approvalRef") || "").trim(),
    expiresAt: String(formData.get("expiresAt") || "").trim(),
  };
  if (!payload.reason || !payload.approvalRef || !payload.expiresAt) {
    setRoleManagementMessage("error", "Reason, approval reference, and expiry date are required.");
    return;
  }
  const isEditing = state.exceptionDraft.mode === "edit" && Boolean(state.exceptionDraft.exceptionId);
  setRoleManagementMessage("info", isEditing ? "Updating direct-user exception..." : "Creating direct-user exception...");
  try {
    const endpoint = isEditing
      ? `/api/admin/access-control/roles/${encodeURIComponent(role.key)}/exceptions/${encodeURIComponent(state.exceptionDraft.exceptionId)}`
      : `/api/admin/access-control/roles/${encodeURIComponent(role.key)}/exceptions`;
    await apiRequest(endpoint, {
      method: isEditing ? "PATCH" : "POST",
      body: payload,
    });
    state.exceptionDraft = emptyExceptionDraft();
    state.search.exception = { query: "", results: [], loading: false, error: "" };
    await refreshRoleData();
    state.activeRoleTab = "exceptions";
    renderRoleManagement();
  } catch (error) {
    renderRoleManagement();
    setRoleManagementMessage("error", escapeHtml(error.message));
  }
}

async function handleRoleAction(event) {
  const action = event.currentTarget.dataset.action;
  const roleKey = event.currentTarget.dataset.roleKey;
  const kind = event.currentTarget.dataset.kind;
  const name = event.currentTarget.dataset.name;
  const tab = event.currentTarget.dataset.tab;
  const exceptionId = event.currentTarget.dataset.exceptionId;
  const displayName = event.currentTarget.dataset.displayName || "";
  const email = event.currentTarget.dataset.email || "";

  if (action === "select-role") {
    state.selectedRoleKey = roleKey;
    state.activeRoleTab = "overview";
    state.exceptionDraft = emptyExceptionDraft();
    state.search.user = { query: "", results: [], loading: false, error: "" };
    state.search.exception = { query: "", results: [], loading: false, error: "" };
    state.search.group = { query: "", results: [], loading: false, error: "" };
    renderRoleCatalog();
    attachRoleCatalogHandlers();
    renderRoleDetail();
    return;
  }

  if (action === "select-role-tab") {
    state.activeRoleTab = tab || "overview";
    renderRoleDetail();
    return;
  }

  if (action === "select-exception-user") {
    state.exceptionDraft = {
      mode: "create",
      exceptionId: "",
      username: name,
      displayName,
      email,
      reason: state.exceptionDraft.reason,
      approvalRef: state.exceptionDraft.approvalRef,
      expiresAt: state.exceptionDraft.expiresAt,
    };
    state.activeRoleTab = "exceptions";
    renderRoleDetail();
    return;
  }

  if (action === "clear-exception-draft") {
    state.exceptionDraft = emptyExceptionDraft();
    renderRoleDetail();
    return;
  }

  if (action === "edit-exception") {
    state.exceptionDraft = {
      mode: "edit",
      exceptionId,
      username: name,
      displayName,
      email,
      reason: event.currentTarget.dataset.reason || "",
      approvalRef: event.currentTarget.dataset.approvalRef || "",
      expiresAt: event.currentTarget.dataset.expiresAt || "",
    };
    state.activeRoleTab = "exceptions";
    renderRoleDetail();
    return;
  }

  if (action === "remove-exception") {
    try {
      setRoleManagementMessage("info", "Removing direct-user exception...");
      await apiRequest(`/api/admin/access-control/roles/${encodeURIComponent(roleKey)}/exceptions/${encodeURIComponent(exceptionId)}`, {
        method: "DELETE",
      });
      await refreshRoleData();
      state.activeRoleTab = "exceptions";
      renderRoleManagement();
      return;
    } catch (error) {
      renderRoleManagement();
      setRoleManagementMessage("error", escapeHtml(error.message));
      return;
    }
  }

  try {
    await mutateRoleMembership(action === "remove-member" ? "DELETE" : "POST", roleKey, kind, name);
    renderRoleCatalog();
    attachRoleCatalogHandlers();
  } catch (error) {
    renderRoleManagement();
    setRoleManagementMessage("error", escapeHtml(error.message));
  }
}

async function loadAdminExperience() {
  renderAdminTools(state.config, state.isAdmin);
  if (!accessControlEnabled() && currentPortalRoute() === "access-control") {
    rememberRouteNotice("info", state.config?.admin?.accessControlNotice || "Use Keycloak Admin and Ranger Admin for access management in this environment.");
    window.location.replace("/");
    return;
  }
  if (currentPortalRoute() === "access-control" && !state.isAdmin) {
    window.location.replace("/");
    return;
  }
  if (!state.isAdmin || !state.config?.admin?.roleManagementEnabled) {
    hide(roleManagementPanel);
    return;
  }

  if (currentPortalRoute() !== "access-control") {
    hide(roleManagementPanel);
    return;
  }

  show(roleManagementPanel);
  setRoleManagementMessage("info", "Loading live access-control state...");
  try {
    await refreshRoleData();
  } catch (error) {
    state.adminStatus = null;
    state.roles = [];
    renderRoleManagement();
    setRoleManagementMessage("error", escapeHtml(error.message));
    return;
  }

  renderRoleManagement();
  attachRoleCatalogHandlers();
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
  if (currentPortalRoute() === "access-control" && !accessControlEnabled()) {
    rememberRouteNotice("info", state.config?.admin?.accessControlNotice || "Use Keycloak Admin and Ranger Admin for access management in this environment.");
    clearTargetSection();
    window.history.replaceState(null, document.title, "/");
  }
  if (window.location.hash === "#administration" || currentPortalRoute() === "access-control") {
    rememberTargetSection("access-control");
  }

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

  const claimName = state.config.identity.groupsClaim || "groups";
  const rawGroups = keycloak.tokenParsed?.[claimName];
  state.groups = Array.isArray(rawGroups) ? rawGroups : [];
  const adminConfig = state.config.admin || {};
  const requiredGroups = adminConfig.requiredGroups || [];
  state.isAdmin = requiredGroups.length > 0 && requiredGroups.some((group) => state.groups.includes(group));
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

  renderApps(state.config, state.groups);
  await refreshHealth();
  if (state.config?.health?.enabled && !state.health.timer) {
    const refreshIntervalSeconds = Number(state.config.health.refreshIntervalSeconds || 90);
    state.health.timer = window.setInterval(() => {
      refreshHealth().catch((error) => {
        console.warn("Periodic health refresh failed.", error);
      });
    }, Math.max(15, refreshIntervalSeconds) * 1000);
  }
  if (accessControlBack) {
    accessControlBack.addEventListener("click", () => {
      window.location.assign("/");
    });
  }
  await loadAdminExperience();
  if (currentPortalRoute() !== "access-control") {
    showHomeRoute();
  }
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
