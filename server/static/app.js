let selectedClientUid = null;
let historyChart = null;
let uptimeChart = null;
let diskChart = null;
let compareChart = null;
let onboardingTokenValue = "";
let currentApiKey = "";
let authContext = null;
let cachedUsers = [];
const currentPage = document.body?.dataset?.page || "dashboard";

const REPOSITORY_URL = "https://github.com/DorDim/projektwoche.git";
const API_KEY_STORAGE_KEY = "hardware-monitor-auth-token";
const PERMISSION_FIELDS = [
  ["view_dashboard", "ViewDashboard"],
  ["add_clients", "AddClients"],
  ["delete_clients", "DeleteClients"],
  ["manage_users", "ManageUsers"],
  ["manage_alert_rules", "ManageAlertRules"],
  ["view_events", "ViewEvents"],
];

function getEl(id) {
  return document.getElementById(id);
}

function bindEvent(id, eventName, handler) {
  const element = getEl(id);
  if (!element) return;
  element.addEventListener(eventName, handler);
}

function markActiveNavigation() {
  const linkMap = {
    dashboard: "navDashboardLink",
    compare: "navCompareLink",
    users: "navUsersLink",
  };
  Object.values(linkMap).forEach((id) => {
    const link = getEl(id);
    if (!link) return;
    link.classList.remove("bg-blue-100", "text-blue-800");
    link.classList.add("text-slate-600");
  });
  const activeLink = getEl(linkMap[currentPage]);
  if (activeLink) {
    activeLink.classList.remove("text-slate-600");
    activeLink.classList.add("bg-blue-100", "text-blue-800");
  }
}

function headers() {
  return { "X-API-Key": currentApiKey };
}

function setCurrentApiKey(newKey, persist = true) {
  currentApiKey = (newKey || "").trim();
  if (persist) {
    persistApiKey();
  }
}

function hasPermission(permissionName) {
  if (!authContext) return false;
  if (authContext.role === "admin") return true;
  return Boolean(authContext.permissions && authContext.permissions[permissionName]);
}

function collectPermissions(prefix) {
  const permissions = {};
  PERMISSION_FIELDS.forEach(([permissionKey, fieldSuffix]) => {
    const checkbox = document.getElementById(`${prefix}${fieldSuffix}`);
    permissions[permissionKey] = Boolean(checkbox?.checked);
  });
  return permissions;
}

function applyPermissions(prefix, permissions) {
  PERMISSION_FIELDS.forEach(([permissionKey, fieldSuffix]) => {
    const checkbox = document.getElementById(`${prefix}${fieldSuffix}`);
    if (!checkbox) return;
    checkbox.checked = Boolean(permissions && permissions[permissionKey]);
  });
}

function setPermissionControlsDisabled(prefix, isDisabled) {
  PERMISSION_FIELDS.forEach(([_permissionKey, fieldSuffix]) => {
    const checkbox = document.getElementById(`${prefix}${fieldSuffix}`);
    if (!checkbox) return;
    checkbox.disabled = isDisabled;
  });
}

function updateAuthUi() {
  const state = getEl("authState");
  if (!state) return;
  const username = authContext?.username || "-";
  const role = authContext?.role || "-";
  state.textContent = `${username} (${role})`;
  getEl("openOnboardingBtn")?.classList.toggle("hidden", !hasPermission("add_clients"));
  getEl("userManagementSection")?.classList.toggle("hidden", !hasPermission("manage_users"));
  getEl("navCompareLink")?.classList.toggle("hidden", !hasPermission("view_dashboard"));
  getEl("navUsersLink")?.classList.toggle("hidden", !hasPermission("manage_users"));
}

function showLoginScreen() {
  getEl("dashboardApp")?.classList.add("hidden");
  getEl("loginScreen")?.classList.remove("hidden");
  getEl("loginScreen")?.classList.add("flex");
}

function showDashboard() {
  getEl("loginScreen")?.classList.add("hidden");
  getEl("loginScreen")?.classList.remove("flex");
  getEl("dashboardApp")?.classList.remove("hidden");
}

function showLoginError(message = "") {
  const hint = getEl("loginError");
  if (!hint) return;
  if (!message) {
    hint.classList.add("hidden");
    hint.textContent = "";
    return;
  }
  hint.textContent = message;
  hint.classList.remove("hidden");
}

function loadSavedApiKey() {
  try {
    const saved = localStorage.getItem(API_KEY_STORAGE_KEY);
    if (saved) {
      currentApiKey = saved.trim();
    }
  } catch (_error) {
    // Local storage might be disabled in hardened browsers.
  }
}

function persistApiKey() {
  try {
    if (currentApiKey) {
      localStorage.setItem(API_KEY_STORAGE_KEY, currentApiKey);
    } else {
      localStorage.removeItem(API_KEY_STORAGE_KEY);
    }
  } catch (_error) {
    // Ignore storage errors; the app still works without persistence.
  }
}

function fmt(value, digits = 2) {
  if (value === null || value === undefined) return "-";
  if (typeof value === "number") return value.toFixed(digits);
  return String(value);
}

function escapeHtml(value) {
  const text = value === null || value === undefined ? "-" : String(value);
  return text
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatDuration(seconds) {
  if (seconds === null || seconds === undefined) return "-";
  const total = Number(seconds);
  if (!Number.isFinite(total) || total < 0) return "-";
  const days = Math.floor(total / 86400);
  const hours = Math.floor((total % 86400) / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  return `${days}d ${hours}h ${minutes}m`;
}

async function apiGet(path) {
  if (!currentApiKey) {
    throw new Error("Nicht angemeldet.");
  }
  const response = await fetch(path, { headers: headers() });
  if (!response.ok) {
    if (response.status === 401) {
      await forceLogout("Sitzung abgelaufen. Bitte erneut anmelden.");
    }
    throw new Error(`HTTP ${response.status}: ${await response.text()}`);
  }
  return response.json();
}

async function apiPost(path, payload = {}) {
  if (!currentApiKey) {
    throw new Error("Nicht angemeldet.");
  }
  const response = await fetch(path, {
    method: "POST",
    headers: { ...headers(), "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    if (response.status === 401) {
      await forceLogout("Sitzung abgelaufen. Bitte erneut anmelden.");
    }
    throw new Error(`HTTP ${response.status}: ${await response.text()}`);
  }
  if (response.status === 204) {
    return null;
  }
  return response.json();
}

async function apiPatch(path, payload = {}) {
  if (!currentApiKey) {
    throw new Error("Nicht angemeldet.");
  }
  const response = await fetch(path, {
    method: "PATCH",
    headers: { ...headers(), "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    if (response.status === 401) {
      await forceLogout("Sitzung abgelaufen. Bitte erneut anmelden.");
    }
    throw new Error(`HTTP ${response.status}: ${await response.text()}`);
  }
  if (response.status === 204) return null;
  return response.json();
}

async function apiDelete(path) {
  if (!currentApiKey) {
    throw new Error("Nicht angemeldet.");
  }
  const response = await fetch(path, {
    method: "DELETE",
    headers: headers(),
  });
  if (!response.ok) {
    if (response.status === 401) {
      await forceLogout("Sitzung abgelaufen. Bitte erneut anmelden.");
    }
    throw new Error(`HTTP ${response.status}: ${await response.text()}`);
  }
  if (response.status === 204) return null;
  return response.json();
}

async function apiPostPublic(path, payload) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${await response.text()}`);
  }
  return response.json();
}

function showError(message) {
  const banner = getEl("errorBanner");
  if (!banner) return;
  if (!message) {
    banner.classList.add("hidden");
    banner.textContent = "";
    return;
  }
  banner.textContent = message;
  banner.classList.remove("hidden");
}

function showOnboardingStatus(message, isError = false) {
  const statusBox = getEl("onboardingStatus");
  if (!statusBox) return;
  statusBox.textContent = message;
  statusBox.className = `rounded-md border px-3 py-2 text-xs ${
    isError
      ? "border-red-200 bg-red-50 text-red-700"
      : "border-emerald-200 bg-emerald-50 text-emerald-700"
  }`;
  statusBox.classList.remove("hidden");
}

function renderClients(clients) {
  const tbody = document.querySelector("#clientsTable tbody");
  if (!tbody) return;
  tbody.innerHTML = "";
  const canDeleteClients = hasPermission("delete_clients") && currentPage === "dashboard";
  const hasDetailsView = Boolean(getEl("detailsTitle"));
  const enableCompareSelection = Boolean(document.querySelector("#compareTable tbody"));

  clients.forEach((client) => {
    const tr = document.createElement("tr");
    tr.className = "cursor-pointer hover:bg-slate-50";
    const statusClass = client.status === "online" ? "text-emerald-700" : "text-red-700";
    const statusDotClass = client.status === "online" ? "bg-emerald-500" : "bg-red-500";
    const selectCell = enableCompareSelection
      ? `<input type="checkbox" data-uid="${escapeHtml(client.client_uid)}" class="compare-check" />`
      : "-";
    tr.innerHTML = `
      <td class="px-3 py-2">${selectCell}</td>
      <td class="px-3 py-2">${escapeHtml(client.hostname)}</td>
      <td class="px-3 py-2 font-mono text-xs">${escapeHtml(client.client_uid)}</td>
      <td class="px-3 py-2 ${statusClass}">
        <div class="flex items-center gap-2 font-semibold">
          <span class="h-2.5 w-2.5 rounded-full ${statusDotClass}"></span>
          <span>${escapeHtml(client.status)}</span>
        </div>
      </td>
      <td class="px-3 py-2">${fmt(client.latest_snapshot?.cpu_threads, 0)}</td>
      <td class="px-3 py-2">${fmt(client.latest_snapshot?.ram_total_mb, 0)}</td>
      <td class="px-3 py-2">${fmt(client.latest_snapshot?.min_disk_free_percent, 2)}</td>
      <td class="px-3 py-2">${new Date(client.last_seen).toLocaleString()}</td>
      <td class="px-3 py-2">
        ${
          canDeleteClients
            ? `<button data-delete-client="${escapeHtml(client.client_uid)}" class="rounded border border-red-300 px-2 py-1 text-xs font-semibold text-red-700 hover:bg-red-50">Löschen</button>`
            : "-"
        }
      </td>
    `;
    tr.addEventListener("click", (event) => {
      if (event.target && event.target.classList.contains("compare-check")) {
        return;
      }
      if (event.target && event.target.dataset && event.target.dataset.deleteClient) {
        return;
      }
      if (!hasDetailsView) {
        return;
      }
      selectedClientUid = client.client_uid;
      loadClientDetails(client.client_uid).catch((error) => showError(error.message));
    });
    tbody.appendChild(tr);
  });

  if (enableCompareSelection) {
    document.querySelectorAll(".compare-check").forEach((checkbox) => {
      checkbox.addEventListener("change", () => {
        loadCompare().catch((error) => showError(error.message));
      });
    });
  }
  document.querySelectorAll("[data-delete-client]").forEach((button) => {
    button.addEventListener("click", async (event) => {
      event.preventDefault();
      event.stopPropagation();
      const clientUid = button.dataset.deleteClient;
      if (!clientUid) return;
      const confirmed = window.confirm(`Client '${clientUid}' wirklich löschen?`);
      if (!confirmed) return;
      try {
        await apiDelete(`/api/clients/${encodeURIComponent(clientUid)}`);
        if (selectedClientUid === clientUid) {
          selectedClientUid = null;
        }
        await refreshAll();
      } catch (error) {
        showError(error.message);
      }
    });
  });
}

function resetDetailView(message) {
  const detailsTitle = getEl("detailsTitle");
  const summaryCards = getEl("hardwareSummaryCards");
  const diskDetailsBody = getEl("diskDetailsBody");
  const adapterDetailsBody = getEl("adapterDetailsBody");
  const gpuDetailsBody = getEl("gpuDetailsBody");
  if (!detailsTitle || !summaryCards || !diskDetailsBody || !adapterDetailsBody || !gpuDetailsBody) {
    return;
  }
  detailsTitle.textContent = "Client-Details";
  summaryCards.innerHTML = `
    <div class="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-500">
      ${escapeHtml(message)}
    </div>
  `;
  diskDetailsBody.innerHTML = "";
  adapterDetailsBody.innerHTML = "";
  gpuDetailsBody.innerHTML = "";
  if (historyChart) historyChart.destroy();
  if (uptimeChart) uptimeChart.destroy();
  if (diskChart) diskChart.destroy();
  historyChart = null;
  uptimeChart = null;
  diskChart = null;
}

function renderResourceHistory(snapshots) {
  const canvas = getEl("historyChart");
  if (!canvas) return;
  const ordered = [...snapshots].reverse();
  const labels = ordered.map((s) => new Date(s.collected_at).toLocaleTimeString());
  const diskFreeMin = ordered.map((s) =>
    s.disks && s.disks.length > 0
      ? Math.min(...s.disks.map((d) => d.free_percent || Number.POSITIVE_INFINITY))
      : null
  );
  const cpuTemp = ordered.map((s) => s.cpu_temperature_c);

  if (historyChart) {
    historyChart.destroy();
  }
  historyChart = new Chart(canvas, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Min. freier Speicher (%)",
          data: diskFreeMin,
          borderColor: "#2563eb",
          yAxisID: "y",
        },
        {
          label: "CPU-Temperatur (°C)",
          data: cpuTemp,
          borderColor: "#dc2626",
          yAxisID: "y1",
        },
      ],
    },
    options: {
      responsive: true,
      scales: {
        y: { position: "left" },
        y1: { position: "right" },
      },
    },
  });
}

function renderUptimeHistory(snapshots) {
  const canvas = getEl("uptimeChart");
  if (!canvas) return;
  const ordered = [...snapshots].reverse();
  const labels = ordered.map((s) => new Date(s.collected_at).toLocaleTimeString());
  const uptimeHours = ordered.map((s) =>
    s.uptime_seconds === null || s.uptime_seconds === undefined ? null : s.uptime_seconds / 3600
  );

  if (uptimeChart) {
    uptimeChart.destroy();
  }
  uptimeChart = new Chart(canvas, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Uptime (Stunden)",
          data: uptimeHours,
          borderColor: "#0f766e",
          backgroundColor: "rgba(15,118,110,0.15)",
          fill: true,
        },
      ],
    },
    options: {
      responsive: true,
      scales: {
        y: { beginAtZero: true },
      },
    },
  });
}

function renderDiskUsageChart(snapshot) {
  const canvas = getEl("diskChart");
  if (!canvas) return;
  const disks = snapshot?.disks || [];
  if (diskChart) {
    diskChart.destroy();
  }
  diskChart = new Chart(canvas, {
    type: "bar",
    data: {
      labels: disks.map((d) => d.mountpoint || "unbekannt"),
      datasets: [
        {
          label: "Freier Speicher (%)",
          data: disks.map((d) => d.free_percent),
          backgroundColor: "#22c55e",
        },
      ],
    },
    options: {
      responsive: true,
      scales: {
        y: { beginAtZero: true, max: 100 },
      },
    },
  });
}

function renderHardwareSummary(snapshot) {
  const container = getEl("hardwareSummaryCards");
  if (!container) return;
  const cards = [
    ["Hostname", snapshot.hostname],
    ["Betriebssystem", snapshot.os_version],
    ["CPU Kerne / Threads", `${fmt(snapshot.cpu_cores, 0)} / ${fmt(snapshot.cpu_threads, 0)}`],
    ["CPU Max-Takt (MHz)", fmt(snapshot.cpu_max_mhz, 2)],
    ["RAM gesamt (MB)", fmt(snapshot.ram_total_mb, 0)],
    ["Uptime", formatDuration(snapshot.uptime_seconds)],
    ["CPU-Temperatur (°C)", fmt(snapshot.cpu_temperature_c, 1)],
    ["Lüfter (RPM)", fmt(snapshot.fan_speed_rpm, 0)],
    ["Mainboard", snapshot.motherboard_vendor],
    ["BIOS/UEFI", snapshot.bios_vendor],
    ["Erfasst am", new Date(snapshot.collected_at).toLocaleString()],
  ];
  container.innerHTML = cards
    .map(
      ([label, value]) => `
      <div class="rounded-lg border border-slate-200 bg-slate-50 p-3">
        <div class="text-xs uppercase tracking-wide text-slate-500">${escapeHtml(label)}</div>
        <div class="mt-1 text-sm font-semibold text-slate-800">${escapeHtml(value)}</div>
      </div>`
    )
    .join("");
}

function renderDiskDetails(disks) {
  const body = getEl("diskDetailsBody");
  if (!body) return;
  if (!disks || disks.length === 0) {
    body.innerHTML =
      '<tr><td class="px-3 py-2 text-slate-500" colspan="4">Keine Laufwerksdaten vorhanden</td></tr>';
    return;
  }
  body.innerHTML = disks
    .map(
      (disk) => `
      <tr>
        <td class="px-3 py-2">${escapeHtml(disk.mountpoint)}</td>
        <td class="px-3 py-2">${escapeHtml(disk.filesystem)}</td>
        <td class="px-3 py-2">${fmt(disk.free_percent, 2)}</td>
        <td class="px-3 py-2">${fmt(disk.free_gb, 2)}</td>
      </tr>`
    )
    .join("");
}

function renderAdapterDetails(adapters) {
  const body = getEl("adapterDetailsBody");
  if (!body) return;
  if (!adapters || adapters.length === 0) {
    body.innerHTML =
      '<tr><td class="px-3 py-2 text-slate-500" colspan="3">Keine Netzwerkdaten vorhanden</td></tr>';
    return;
  }
  body.innerHTML = adapters
    .map(
      (adapter) => `
      <tr>
        <td class="px-3 py-2">${escapeHtml(adapter.name)}</td>
        <td class="px-3 py-2">${escapeHtml((adapter.ipv4 || []).join(", "))}</td>
        <td class="px-3 py-2">${escapeHtml(adapter.mac)}</td>
      </tr>`
    )
    .join("");
}

function renderGpuDetails(gpus) {
  const body = getEl("gpuDetailsBody");
  if (!body) return;
  if (!gpus || gpus.length === 0) {
    body.innerHTML = '<tr><td class="px-3 py-2 text-slate-500" colspan="3">Keine GPU-Daten vorhanden</td></tr>';
    return;
  }
  body.innerHTML = gpus
    .map(
      (gpu) => `
      <tr>
        <td class="px-3 py-2">${escapeHtml(gpu.name || gpu.model || "-")}</td>
        <td class="px-3 py-2">${fmt(gpu.memory_mb, 0)}</td>
        <td class="px-3 py-2">${escapeHtml(gpu.driver || "-")}</td>
      </tr>`
    )
    .join("");
}

function renderHardwareDetails(snapshot) {
  renderHardwareSummary(snapshot);
  renderDiskDetails(snapshot.disks || []);
  renderAdapterDetails(snapshot.network_adapters || []);
  renderGpuDetails(snapshot.gpu_info || []);
}

function renderCompareVisuals(rows) {
  const cards = getEl("compareSummaryCards");
  const chartCanvas = getEl("compareChart");
  if (!cards || !chartCanvas) return;
  if (!rows || rows.length === 0) {
    cards.innerHTML = `
      <div class="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-500">
        Wähle Clients über die Checkboxen, um den Vergleich zu sehen.
      </div>
    `;
    if (compareChart) {
      compareChart.destroy();
      compareChart = null;
    }
    return;
  }

  const topRam = [...rows]
    .filter((row) => row.ram_total_mb !== null && row.ram_total_mb !== undefined)
    .sort((a, b) => (b.ram_total_mb || 0) - (a.ram_total_mb || 0))[0];
  const bestDisk = [...rows]
    .filter((row) => row.min_disk_free_percent !== null && row.min_disk_free_percent !== undefined)
    .sort((a, b) => (b.min_disk_free_percent || 0) - (a.min_disk_free_percent || 0))[0];
  const avgThreads =
    rows.length > 0
      ? rows
          .map((row) => row.cpu_threads || 0)
          .reduce((total, value) => total + value, 0) / rows.length
      : null;

  cards.innerHTML = `
    <div class="rounded-lg border border-blue-200 bg-blue-50 p-3">
      <div class="text-xs uppercase tracking-wide text-blue-600">Höchster RAM</div>
      <div class="mt-1 text-sm font-semibold text-blue-900">${escapeHtml(
        topRam ? `${topRam.hostname} (${fmt(topRam.ram_total_mb, 0)} MB)` : "-"
      )}</div>
    </div>
    <div class="rounded-lg border border-emerald-200 bg-emerald-50 p-3">
      <div class="text-xs uppercase tracking-wide text-emerald-600">Bester freier Speicher</div>
      <div class="mt-1 text-sm font-semibold text-emerald-900">${escapeHtml(
        bestDisk ? `${bestDisk.hostname} (${fmt(bestDisk.min_disk_free_percent, 2)}%)` : "-"
      )}</div>
    </div>
    <div class="rounded-lg border border-violet-200 bg-violet-50 p-3">
      <div class="text-xs uppercase tracking-wide text-violet-600">Ø CPU Threads</div>
      <div class="mt-1 text-sm font-semibold text-violet-900">${fmt(avgThreads, 1)}</div>
    </div>
  `;

  if (compareChart) {
    compareChart.destroy();
  }
  compareChart = new Chart(chartCanvas, {
    type: "bar",
    data: {
      labels: rows.map((row) => row.hostname),
      datasets: [
        {
          label: "RAM (MB)",
          data: rows.map((row) => row.ram_total_mb),
          backgroundColor: "#2563eb",
          yAxisID: "y",
        },
        {
          label: "Freier Speicher min (%)",
          data: rows.map((row) => row.min_disk_free_percent),
          backgroundColor: "#16a34a",
          yAxisID: "y1",
        },
      ],
    },
    options: {
      responsive: true,
      scales: {
        y: { position: "left", beginAtZero: true },
        y1: { position: "right", beginAtZero: true, max: 100 },
      },
    },
  });
}

async function loadClientDetails(clientUid) {
  if (!getEl("detailsTitle")) return;
  const snapshots = await apiGet(`/api/clients/${clientUid}/snapshots?limit=100`);
  if (!snapshots || snapshots.length === 0) {
    resetDetailView("Für diesen Client sind noch keine Snapshots vorhanden.");
    return;
  }
  const latest = snapshots[0];
  getEl("detailsTitle").textContent = `Client-Details: ${latest.hostname} (${clientUid})`;
  renderHardwareDetails(latest);
  renderResourceHistory(snapshots);
  renderUptimeHistory(snapshots);
  renderDiskUsageChart(latest);
}

async function loadCompare() {
  const checked = [...document.querySelectorAll(".compare-check:checked")].map((el) => el.dataset.uid);
  const tbody = document.querySelector("#compareTable tbody");
  if (!tbody) return;
  tbody.innerHTML = "";
  if (checked.length === 0) {
    renderCompareVisuals([]);
    return;
  }
  const query = checked.map((uid) => `client_uids=${encodeURIComponent(uid)}`).join("&");
  const rows = await apiGet(`/api/compare?${query}`);
  renderCompareVisuals(rows);
  rows.forEach((row) => {
    const tr = document.createElement("tr");
    const diskPercent = row.min_disk_free_percent ?? 0;
    tr.innerHTML = `
      <td class="px-3 py-2">${escapeHtml(row.hostname)}</td>
      <td class="px-3 py-2 font-mono text-xs">${escapeHtml(row.client_uid)}</td>
      <td class="px-3 py-2">${fmt(row.cpu_threads, 0)}</td>
      <td class="px-3 py-2">${fmt(row.ram_total_mb, 0)}</td>
      <td class="px-3 py-2">
        <div class="flex items-center gap-2">
          <div class="h-2 w-24 overflow-hidden rounded bg-slate-200">
            <div class="h-full ${diskPercent < 10 ? "bg-red-500" : "bg-emerald-500"}" style="width:${Math.max(
      0,
      Math.min(100, diskPercent)
    )}%"></div>
          </div>
          <span>${fmt(row.min_disk_free_percent, 2)}%</span>
        </div>
      </td>
      <td class="px-3 py-2">${fmt(row.uptime_seconds, 0)}</td>
    `;
    tbody.appendChild(tr);
  });
}

async function loadAlerts() {
  const tbody = document.querySelector("#alertsTable tbody");
  if (!tbody) return;
  const alerts = await apiGet("/api/alerts?limit=100");
  tbody.innerHTML = "";
  alerts.forEach((alert) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td class="px-3 py-2">${new Date(alert.triggered_at).toLocaleString()}</td>
      <td class="px-3 py-2">${escapeHtml(alert.client_uid)}</td>
      <td class="px-3 py-2">${escapeHtml(alert.rule_name)}</td>
      <td class="px-3 py-2">${fmt(alert.metric_value, 2)}</td>
      <td class="px-3 py-2">${escapeHtml(alert.message)}</td>
    `;
    tbody.appendChild(tr);
  });
}

function permissionSummaryText(user) {
  if (user.role === "admin") {
    return "Alle";
  }
  const labels = {
    view_dashboard: "Dashboard",
    add_clients: "Clients+",
    delete_clients: "Clients-",
    manage_users: "Nutzer",
    manage_alert_rules: "Alerts",
    view_events: "Events",
  };
  const active = Object.entries(user.permissions || {})
    .filter(([, enabled]) => Boolean(enabled))
    .map(([key]) => labels[key] || key);
  return active.length > 0 ? active.join(", ") : "Keine";
}

function showEditUserHint(message = "") {
  const hint = document.getElementById("editUserHint");
  if (!message) {
    hint.textContent = "";
    hint.classList.add("hidden");
    return;
  }
  hint.textContent = message;
  hint.classList.remove("hidden");
}

function applyRoleToPermissionForm(prefix, roleValue) {
  const isAdmin = roleValue === "admin";
  if (isAdmin) {
    applyPermissions(prefix, {
      view_dashboard: true,
      add_clients: true,
      delete_clients: true,
      manage_users: true,
      manage_alert_rules: true,
      view_events: true,
    });
  }
  setPermissionControlsDisabled(prefix, isAdmin);
}

function openEditUserModal(userId) {
  const user = cachedUsers.find((entry) => entry.id === Number(userId));
  if (!user) {
    showError("Benutzer nicht gefunden.");
    return;
  }
  document.getElementById("editUserId").value = String(user.id);
  document.getElementById("editUserUsername").value = user.username;
  document.getElementById("editUserPassword").value = "";
  document.getElementById("editUserRole").value = user.role;
  document.getElementById("editUserActive").checked = Boolean(user.is_active);
  applyPermissions("editPerm", user.permissions || {});
  applyRoleToPermissionForm("editPerm", user.role);
  showEditUserHint("");
  const modal = document.getElementById("editUserModal");
  modal.classList.remove("hidden");
  modal.classList.add("flex");
}

function closeEditUserModal() {
  const modal = document.getElementById("editUserModal");
  modal.classList.add("hidden");
  modal.classList.remove("flex");
  showEditUserHint("");
}

function renderUsers(users) {
  cachedUsers = users;
  const tbody = document.querySelector("#usersTable tbody");
  tbody.innerHTML = "";
  users.forEach((user) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td class="px-3 py-2 font-medium">${escapeHtml(user.username)}</td>
      <td class="px-3 py-2">${escapeHtml(user.role)}</td>
      <td class="px-3 py-2 text-xs">${escapeHtml(permissionSummaryText(user))}</td>
      <td class="px-3 py-2">${user.is_active ? "Ja" : "Nein"}</td>
      <td class="px-3 py-2 space-x-2">
        <button data-edit-user="${user.id}" class="rounded border border-indigo-300 px-2 py-1 text-xs font-semibold text-indigo-700 hover:bg-indigo-50">Bearbeiten</button>
        <button data-delete-user="${user.id}" class="rounded border border-red-300 px-2 py-1 text-xs font-semibold text-red-700 hover:bg-red-50">Löschen</button>
      </td>
    `;
    tbody.appendChild(tr);
  });
  document.querySelectorAll("[data-edit-user]").forEach((button) => {
    button.addEventListener("click", () => {
      const userId = button.dataset.editUser;
      if (!userId) return;
      openEditUserModal(userId);
    });
  });
  document.querySelectorAll("[data-delete-user]").forEach((button) => {
    button.addEventListener("click", async () => {
      const userId = button.dataset.deleteUser;
      if (!userId) return;
      if (!window.confirm("Benutzer wirklich löschen?")) return;
      try {
        await apiDelete(`/api/users/${userId}`);
        await loadUsers();
      } catch (error) {
        showError(error.message);
      }
    });
  });
}

async function loadUsers() {
  if (!document.querySelector("#usersTable tbody")) {
    return;
  }
  if (!hasPermission("manage_users")) {
    return;
  }
  const users = await apiGet("/api/users");
  renderUsers(users);
}

async function createUserFromForm(event) {
  event.preventDefault();
  const usernameInput = document.getElementById("newUserUsername");
  const passwordInput = document.getElementById("newUserPassword");
  const roleInput = document.getElementById("newUserRole");
  const username = usernameInput.value.trim();
  const password = passwordInput.value;
  if (!username || !password) {
    showError("Benutzername und Passwort sind erforderlich.");
    return;
  }
  try {
    await apiPost("/api/users", {
      username,
      password,
      role: roleInput.value,
      permissions: collectPermissions("perm"),
      is_active: true,
    });
    usernameInput.value = "";
    passwordInput.value = "";
    roleInput.value = "user";
    applyPermissions("perm", {
      view_dashboard: true,
      add_clients: false,
      delete_clients: false,
      manage_users: false,
      manage_alert_rules: false,
      view_events: false,
    });
    applyRoleToPermissionForm("perm", "user");
    await loadUsers();
    showError("");
  } catch (error) {
    showError(error.message);
  }
}

async function updateUserFromForm(event) {
  event.preventDefault();
  const userId = Number(document.getElementById("editUserId").value || 0);
  if (!userId) {
    showEditUserHint("Ungültiger Benutzer.");
    return;
  }
  const role = document.getElementById("editUserRole").value;
  const password = document.getElementById("editUserPassword").value;
  const payload = {
    role,
    permissions: collectPermissions("editPerm"),
    is_active: document.getElementById("editUserActive").checked,
  };
  if (password.trim()) {
    payload.password = password;
  }
  try {
    await apiPatch(`/api/users/${userId}`, payload);
    closeEditUserModal();
    await loadUsers();
    showError("");
  } catch (error) {
    showEditUserHint(`Speichern fehlgeschlagen: ${error.message}`);
  }
}

function buildSetupCommandsWindows(serverOrigin, token) {
  return `powershell -NoProfile -ExecutionPolicy Bypass -Command "git clone ${REPOSITORY_URL}; cd projektwoche; powershell -ExecutionPolicy Bypass -File .\\client\\install_windows_background.ps1 -ServerUrl '${serverOrigin}' -ApiKey '${token}' -IntervalSeconds 60 -StartNow"`;
}

function buildSetupCommandsLinux(serverOrigin, token) {
  return `bash -lc 'git clone ${REPOSITORY_URL} && cd projektwoche && bash ./client/install_linux_background.sh --server-url "${serverOrigin}" --api-key "${token}" --interval-seconds 60'`;
}

function openOnboardingModal() {
  const modal = getEl("onboardingModal");
  if (!modal) return;
  modal.classList.remove("hidden");
  modal.classList.add("flex");
}

function closeOnboardingModal() {
  const modal = getEl("onboardingModal");
  if (!modal) return;
  modal.classList.add("hidden");
  modal.classList.remove("flex");
}

async function generateOnboardingToken() {
  const tokenPayload = await apiPost("/api/onboarding-tokens", {});
  onboardingTokenValue = tokenPayload.token;
  const generatedToken = getEl("generatedToken");
  const serverOrigin = getEl("serverOriginValue");
  const serverHost = getEl("serverHostValue");
  const setupWindows = getEl("setupCommandsWindows");
  const setupLinux = getEl("setupCommandsLinux");
  if (!generatedToken || !serverOrigin || !serverHost || !setupWindows || !setupLinux) {
    return;
  }
  generatedToken.value = tokenPayload.token;
  serverOrigin.textContent = tokenPayload.server_origin;
  serverHost.textContent = tokenPayload.server_host;
  setupWindows.textContent = buildSetupCommandsWindows(
    tokenPayload.server_origin,
    tokenPayload.token
  );
  setupLinux.textContent = buildSetupCommandsLinux(
    tokenPayload.server_origin,
    tokenPayload.token
  );
  showOnboardingStatus("Neuer Client-Token wurde erfolgreich generiert.");
}

function fallbackCopyText(text) {
  const textArea = document.createElement("textarea");
  textArea.value = text;
  textArea.setAttribute("readonly", "");
  textArea.style.position = "absolute";
  textArea.style.left = "-9999px";
  document.body.appendChild(textArea);
  textArea.select();
  const wasCopied = document.execCommand("copy");
  document.body.removeChild(textArea);
  return wasCopied;
}

async function copyTextToClipboard(text) {
  if (!text) {
    throw new Error("Kein Token vorhanden.");
  }
  if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
    await navigator.clipboard.writeText(text);
    return;
  }
  const wasCopied = fallbackCopyText(text);
  if (!wasCopied) {
    throw new Error("Zwischenablage wird vom Browser nicht unterstützt.");
  }
}

async function refreshAll() {
  showError("");
  const hasClientsTable = Boolean(document.querySelector("#clientsTable tbody"));
  const hasCompareTable = Boolean(document.querySelector("#compareTable tbody"));
  const hasDetails = Boolean(getEl("detailsTitle"));
  const hasAlerts = Boolean(document.querySelector("#alertsTable tbody"));
  const hasUsersTable = Boolean(document.querySelector("#usersTable tbody"));
  const needsClientData = hasClientsTable || hasCompareTable || hasDetails || hasAlerts;

  let clients = [];
  if (needsClientData) {
    if (!hasPermission("view_dashboard")) {
      throw new Error("Keine Berechtigung für Dashboard-/Vergleichsdaten.");
    }
    clients = await apiGet("/api/clients");
    if (hasClientsTable) {
      renderClients(clients);
    }
  }

  if (hasAlerts) {
    await loadAlerts();
  }

  if (hasPermission("manage_users")) {
    await loadUsers();
  } else if (hasUsersTable) {
    showError("Keine Berechtigung für die Nutzerverwaltung.");
  }

  if (hasDetails) {
    if (selectedClientUid) {
      await loadClientDetails(selectedClientUid);
    } else if (clients.length > 0) {
      selectedClientUid = clients[0].client_uid;
      await loadClientDetails(selectedClientUid);
    } else {
      resetDetailView("Noch keine Client-Daten vorhanden");
    }
  } else {
    selectedClientUid = null;
  }
}

async function loadAuthContext() {
  authContext = await apiGet("/api/me");
  updateAuthUi();
}

async function initializeSession() {
  if (!currentApiKey) {
    showLoginScreen();
    return;
  }
  await loadAuthContext();
  showDashboard();
  try {
    await refreshAll();
  } catch (error) {
    showError(error.message);
  }
}

async function forceLogout(message = "") {
  setCurrentApiKey("", false);
  authContext = null;
  cachedUsers = [];
  persistApiKey();
  showLoginScreen();
  updateAuthUi();
  resetDetailView("Bitte anmelden, um Daten zu laden.");
  showError("");
  if (message) {
    showLoginError(message);
  }
}

async function handleLoginSubmit(event) {
  event.preventDefault();
  const username = document.getElementById("loginUsername").value.trim();
  const password = document.getElementById("loginPassword").value;
  if (!username || !password) {
    showLoginError("Bitte Benutzername und Passwort eingeben.");
    return;
  }
  try {
    showLoginError("");
    const result = await apiPostPublic("/api/auth/login", { username, password });
    if (!result.token) {
      throw new Error("Login erfolgreich, aber kein Token zurückgegeben.");
    }
    setCurrentApiKey(result.token);
    await initializeSession();
    document.getElementById("loginPassword").value = "";
  } catch (error) {
    showLoginError(`Login fehlgeschlagen: ${error.message}`);
  }
}

async function handleLogout() {
  if (currentApiKey) {
    try {
      await apiPost("/api/auth/logout", {});
    } catch (_error) {
      // Ignore logout API errors and clear local session anyway.
    }
  }
  await forceLogout("Abgemeldet.");
}

bindEvent("refreshBtn", "click", async () => {
  try {
    await refreshAll();
  } catch (error) {
    showError(error.message);
  }
});

bindEvent("openOnboardingBtn", "click", async () => {
  if (!hasPermission("add_clients")) {
    showError("Keine Berechtigung zum Erstellen von Client-Tokens.");
    return;
  }
  openOnboardingModal();
  try {
    await generateOnboardingToken();
  } catch (error) {
    showOnboardingStatus(
      `Token konnte nicht erstellt werden. Nutze den Admin-API-Key. Details: ${error.message}`,
      true
    );
  }
});

bindEvent("createUserForm", "submit", createUserFromForm);
bindEvent("editUserForm", "submit", updateUserFromForm);
bindEvent("loginForm", "submit", handleLoginSubmit);
bindEvent("logoutBtn", "click", () => {
  handleLogout().catch((error) => showError(error.message));
});
bindEvent("newUserRole", "change", (event) => {
  applyRoleToPermissionForm("perm", event.target.value);
});
bindEvent("editUserRole", "change", (event) => {
  applyRoleToPermissionForm("editPerm", event.target.value);
});
bindEvent("closeEditUserModalBtn", "click", closeEditUserModal);
bindEvent("cancelEditUserBtn", "click", closeEditUserModal);
bindEvent("closeOnboardingBtn", "click", closeOnboardingModal);
bindEvent("regenerateTokenBtn", "click", async () => {
  try {
    await generateOnboardingToken();
  } catch (error) {
    showOnboardingStatus(`Token konnte nicht neu generiert werden: ${error.message}`, true);
  }
});

bindEvent("copyTokenBtn", "click", async () => {
  try {
    await copyTextToClipboard(onboardingTokenValue);
    showOnboardingStatus("Token wurde in die Zwischenablage kopiert.");
  } catch (error) {
    showOnboardingStatus(`Kopieren fehlgeschlagen: ${error.message}`, true);
  }
});

bindEvent("onboardingModal", "click", (event) => {
  if (event.target.id === "onboardingModal") {
    closeOnboardingModal();
  }
});
bindEvent("editUserModal", "click", (event) => {
  if (event.target.id === "editUserModal") {
    closeEditUserModal();
  }
});

applyPermissions("perm", {
  view_dashboard: true,
  add_clients: false,
  delete_clients: false,
  manage_users: false,
  manage_alert_rules: false,
  view_events: false,
});
applyRoleToPermissionForm("perm", "user");
markActiveNavigation();

loadSavedApiKey();
if (currentApiKey) {
  initializeSession().catch(async (_error) => {
    await forceLogout("Gespeicherte Sitzung ist ungültig. Bitte erneut anmelden.");
  });
} else {
  forceLogout("").catch(() => undefined);
}
