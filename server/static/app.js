let selectedClientUid = null;
let historyChart = null;
let uptimeChart = null;
let diskChart = null;
let onboardingTokenValue = "";
let currentApiKey = "";

const REPOSITORY_URL = "https://github.com/DorDim/projektwoche.git";
const API_KEY_STORAGE_KEY = "hardware-monitor-api-key";

function headers() {
  return { "X-API-Key": currentApiKey };
}

function setApiKeyState() {
  const state = document.getElementById("apiKeyState");
  const hasKey = Boolean(currentApiKey);
  state.textContent = hasKey ? "API-Key gesetzt" : "Kein API-Key gesetzt";
  state.className = hasKey ? "mt-1 text-sm font-medium text-emerald-700" : "mt-1 text-sm font-medium text-amber-700";
  document.getElementById("openApiKeyModalBtn").textContent = hasKey ? "API-Key ändern" : "API-Key setzen";
}

function showApiKeyHint(message = "") {
  const hint = document.getElementById("apiKeyModalHint");
  if (!message) {
    hint.textContent = "";
    hint.classList.add("hidden");
    return;
  }
  hint.textContent = message;
  hint.classList.remove("hidden");
}

function openApiKeyModal(message = "") {
  const modal = document.getElementById("apiKeyModal");
  const input = document.getElementById("apiKeyModalInput");
  input.value = currentApiKey;
  showApiKeyHint(message);
  modal.classList.remove("hidden");
  modal.classList.add("flex");
  setTimeout(() => input.focus(), 0);
}

function closeApiKeyModal() {
  const modal = document.getElementById("apiKeyModal");
  modal.classList.add("hidden");
  modal.classList.remove("flex");
  showApiKeyHint("");
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
  setApiKeyState();
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
  setApiKeyState();
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
    openApiKeyModal("Bitte zuerst einen API-Key eingeben.");
    throw new Error("Kein API-Key gesetzt.");
  }
  const response = await fetch(path, { headers: headers() });
  if (!response.ok) {
    if (response.status === 401) {
      openApiKeyModal("API-Key ungültig oder abgelaufen. Bitte neu eingeben.");
    }
    throw new Error(`HTTP ${response.status}: ${await response.text()}`);
  }
  return response.json();
}

async function apiPost(path, payload) {
  if (!currentApiKey) {
    openApiKeyModal("Bitte zuerst einen API-Key eingeben.");
    throw new Error("Kein API-Key gesetzt.");
  }
  const response = await fetch(path, {
    method: "POST",
    headers: { ...headers(), "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    if (response.status === 401) {
      openApiKeyModal("API-Key ungültig oder abgelaufen. Bitte neu eingeben.");
    }
    throw new Error(`HTTP ${response.status}: ${await response.text()}`);
  }
  return response.json();
}

function showError(message) {
  const banner = document.getElementById("errorBanner");
  if (!message) {
    banner.classList.add("hidden");
    banner.textContent = "";
    return;
  }
  banner.textContent = message;
  banner.classList.remove("hidden");
}

function showOnboardingStatus(message, isError = false) {
  const statusBox = document.getElementById("onboardingStatus");
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
  tbody.innerHTML = "";

  clients.forEach((client) => {
    const tr = document.createElement("tr");
    tr.className = "cursor-pointer hover:bg-slate-50";
    const statusClass = client.status === "online" ? "text-emerald-700" : "text-red-700";
    const statusDotClass = client.status === "online" ? "bg-emerald-500" : "bg-red-500";
    tr.innerHTML = `
      <td class="px-3 py-2"><input type="checkbox" data-uid="${escapeHtml(client.client_uid)}" class="compare-check" /></td>
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
    `;
    tr.addEventListener("click", (event) => {
      if (event.target && event.target.classList.contains("compare-check")) {
        return;
      }
      selectedClientUid = client.client_uid;
      loadClientDetails(client.client_uid).catch((error) => showError(error.message));
    });
    tbody.appendChild(tr);
  });

  document.querySelectorAll(".compare-check").forEach((checkbox) => {
    checkbox.addEventListener("change", () => {
      loadCompare().catch((error) => showError(error.message));
    });
  });
}

function resetDetailView(message) {
  document.getElementById("detailsTitle").textContent = "Client-Details";
  document.getElementById("hardwareSummaryCards").innerHTML = `
    <div class="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-500">
      ${escapeHtml(message)}
    </div>
  `;
  document.getElementById("diskDetailsBody").innerHTML = "";
  document.getElementById("adapterDetailsBody").innerHTML = "";
  document.getElementById("gpuDetailsBody").innerHTML = "";
  if (historyChart) historyChart.destroy();
  if (uptimeChart) uptimeChart.destroy();
  if (diskChart) diskChart.destroy();
  historyChart = null;
  uptimeChart = null;
  diskChart = null;
}

function renderResourceHistory(snapshots) {
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
  historyChart = new Chart(document.getElementById("historyChart"), {
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
  const ordered = [...snapshots].reverse();
  const labels = ordered.map((s) => new Date(s.collected_at).toLocaleTimeString());
  const uptimeHours = ordered.map((s) =>
    s.uptime_seconds === null || s.uptime_seconds === undefined ? null : s.uptime_seconds / 3600
  );

  if (uptimeChart) {
    uptimeChart.destroy();
  }
  uptimeChart = new Chart(document.getElementById("uptimeChart"), {
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
  const disks = snapshot?.disks || [];
  if (diskChart) {
    diskChart.destroy();
  }
  diskChart = new Chart(document.getElementById("diskChart"), {
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
  document.getElementById("hardwareSummaryCards").innerHTML = cards
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
  const body = document.getElementById("diskDetailsBody");
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
  const body = document.getElementById("adapterDetailsBody");
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
  const body = document.getElementById("gpuDetailsBody");
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

async function loadClientDetails(clientUid) {
  const snapshots = await apiGet(`/api/clients/${clientUid}/snapshots?limit=100`);
  if (!snapshots || snapshots.length === 0) {
    resetDetailView("Für diesen Client sind noch keine Snapshots vorhanden.");
    return;
  }
  const latest = snapshots[0];
  document.getElementById("detailsTitle").textContent = `Client-Details: ${latest.hostname} (${clientUid})`;
  renderHardwareDetails(latest);
  renderResourceHistory(snapshots);
  renderUptimeHistory(snapshots);
  renderDiskUsageChart(latest);
}

async function loadCompare() {
  const checked = [...document.querySelectorAll(".compare-check:checked")].map((el) => el.dataset.uid);
  const tbody = document.querySelector("#compareTable tbody");
  tbody.innerHTML = "";
  if (checked.length === 0) {
    return;
  }
  const query = checked.map((uid) => `client_uids=${encodeURIComponent(uid)}`).join("&");
  const rows = await apiGet(`/api/compare?${query}`);
  rows.forEach((row) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td class="px-3 py-2">${escapeHtml(row.hostname)}</td>
      <td class="px-3 py-2 font-mono text-xs">${escapeHtml(row.client_uid)}</td>
      <td class="px-3 py-2">${fmt(row.cpu_threads, 0)}</td>
      <td class="px-3 py-2">${fmt(row.ram_total_mb, 0)}</td>
      <td class="px-3 py-2">${fmt(row.min_disk_free_percent, 2)}</td>
      <td class="px-3 py-2">${fmt(row.uptime_seconds, 0)}</td>
    `;
    tbody.appendChild(tr);
  });
}

async function loadAlerts() {
  const alerts = await apiGet("/api/alerts?limit=100");
  const tbody = document.querySelector("#alertsTable tbody");
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

function buildSetupCommandsWindows(serverOrigin, token) {
  return [
    `git clone ${REPOSITORY_URL}`,
    "cd projektwoche",
    "",
    "python -m venv .venv",
    ".\\.venv\\Scripts\\Activate.ps1",
    "pip install -r requirements.txt",
    "",
    `powershell -ExecutionPolicy Bypass -File .\\client\\install_windows_background.ps1 -ServerUrl "${serverOrigin}" -ApiKey "${token}" -IntervalSeconds 60 -StartNow`,
    "",
    "# Optional prüfen:",
    'Get-ScheduledTask -TaskName "HardwareMonitorClientAgent"',
  ].join("\n");
}

function buildSetupCommandsLinux(serverOrigin, token) {
  return `git clone ${REPOSITORY_URL}
cd projektwoche

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export SERVER_URL="${serverOrigin}"
export SERVER_API_KEY="${token}"
export AGENT_INTERVAL_SECONDS=60

python -m client.agent`;
}

function openOnboardingModal() {
  const modal = document.getElementById("onboardingModal");
  modal.classList.remove("hidden");
  modal.classList.add("flex");
}

function closeOnboardingModal() {
  const modal = document.getElementById("onboardingModal");
  modal.classList.add("hidden");
  modal.classList.remove("flex");
}

async function generateOnboardingToken() {
  const tokenPayload = await apiPost("/api/onboarding-tokens", {});
  onboardingTokenValue = tokenPayload.token;
  document.getElementById("generatedToken").value = tokenPayload.token;
  document.getElementById("serverOriginValue").textContent = tokenPayload.server_origin;
  document.getElementById("serverHostValue").textContent = tokenPayload.server_host;
  document.getElementById("setupCommandsWindows").textContent = buildSetupCommandsWindows(
    tokenPayload.server_origin,
    tokenPayload.token
  );
  document.getElementById("setupCommandsLinux").textContent = buildSetupCommandsLinux(
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
  if (!currentApiKey) {
    resetDetailView("Bitte API-Key setzen, um Client-Daten zu laden.");
    openApiKeyModal("Bitte zuerst einen API-Key eingeben.");
    return;
  }
  const clients = await apiGet("/api/clients");
  renderClients(clients);
  await loadAlerts();
  if (selectedClientUid) {
    await loadClientDetails(selectedClientUid);
  } else if (clients.length > 0) {
    selectedClientUid = clients[0].client_uid;
    await loadClientDetails(selectedClientUid);
  } else {
    resetDetailView("Noch keine Client-Daten vorhanden");
  }
}

async function saveApiKeyFromModal() {
  const input = document.getElementById("apiKeyModalInput");
  const newKey = input.value.trim();
  if (!newKey) {
    showApiKeyHint("Bitte einen API-Key eingeben.");
    return;
  }
  currentApiKey = newKey;
  persistApiKey();
  closeApiKeyModal();
  showError("");
  await refreshAll();
}

document.getElementById("refreshBtn").addEventListener("click", async () => {
  try {
    await refreshAll();
  } catch (error) {
    showError(error.message);
  }
});

document.getElementById("openOnboardingBtn").addEventListener("click", async () => {
  if (!currentApiKey) {
    openApiKeyModal("Für das Onboarding wird ein API-Key benötigt.");
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

document.getElementById("closeOnboardingBtn").addEventListener("click", closeOnboardingModal);
document.getElementById("regenerateTokenBtn").addEventListener("click", async () => {
  try {
    await generateOnboardingToken();
  } catch (error) {
    showOnboardingStatus(`Token konnte nicht neu generiert werden: ${error.message}`, true);
  }
});

document.getElementById("copyTokenBtn").addEventListener("click", async () => {
  try {
    await copyTextToClipboard(onboardingTokenValue);
    showOnboardingStatus("Token wurde in die Zwischenablage kopiert.");
  } catch (error) {
    showOnboardingStatus(`Kopieren fehlgeschlagen: ${error.message}`, true);
  }
});

document.getElementById("onboardingModal").addEventListener("click", (event) => {
  if (event.target.id === "onboardingModal") {
    closeOnboardingModal();
  }
});

document.getElementById("openApiKeyModalBtn").addEventListener("click", () => openApiKeyModal(""));
document.getElementById("closeApiKeyModalBtn").addEventListener("click", closeApiKeyModal);
document.getElementById("cancelApiKeyBtn").addEventListener("click", closeApiKeyModal);
document.getElementById("saveApiKeyBtn").addEventListener("click", async () => {
  try {
    await saveApiKeyFromModal();
  } catch (error) {
    showError(error.message);
  }
});
document.getElementById("apiKeyModalInput").addEventListener("keydown", async (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    try {
      await saveApiKeyFromModal();
    } catch (error) {
      showError(error.message);
    }
  }
});
document.getElementById("apiKeyModal").addEventListener("click", (event) => {
  if (event.target.id === "apiKeyModal") {
    closeApiKeyModal();
  }
});

loadSavedApiKey();
if (currentApiKey) {
  refreshAll().catch((error) => showError(error.message));
} else {
  resetDetailView("Bitte API-Key setzen, um Daten zu laden.");
  openApiKeyModal("Bitte API-Key eingeben.");
}
