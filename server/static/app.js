let selectedClientUid = null;
let historyChart = null;
let onboardingTokenValue = "";

function headers() {
  const apiKey = document.getElementById("apiKey").value;
  return { "X-API-Key": apiKey };
}

function fmt(value, digits = 2) {
  if (value === null || value === undefined) return "-";
  if (typeof value === "number") return value.toFixed(digits);
  return String(value);
}

async function apiGet(path) {
  const response = await fetch(path, { headers: headers() });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${await response.text()}`);
  }
  return response.json();
}

async function apiPost(path, payload) {
  const response = await fetch(path, {
    method: "POST",
    headers: { ...headers(), "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
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
    tr.innerHTML = `
      <td class="px-3 py-2"><input type="checkbox" data-uid="${client.client_uid}" class="compare-check" /></td>
      <td class="px-3 py-2">${client.hostname}</td>
      <td class="px-3 py-2 font-mono text-xs">${client.client_uid}</td>
      <td class="px-3 py-2 font-semibold ${statusClass}">${client.status}</td>
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

function renderHistory(snapshots) {
  const labels = [...snapshots].reverse().map((s) => new Date(s.collected_at).toLocaleTimeString());
  const disk = [...snapshots]
    .reverse()
    .map((s) =>
      s.disks && s.disks.length > 0
        ? Math.min(...s.disks.map((d) => d.free_percent || Number.POSITIVE_INFINITY))
        : null
    );
  const cpuTemp = [...snapshots].reverse().map((s) => s.cpu_temperature_c);

  const ctx = document.getElementById("historyChart");
  if (historyChart) {
    historyChart.destroy();
  }
  historyChart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Min. freier Speicher (%)",
          data: disk,
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

function renderSnapshotDetails(snapshot) {
  const pre = document.getElementById("snapshotDetails");
  if (!snapshot) {
    pre.textContent = "Keine Daten vorhanden";
    return;
  }
  pre.textContent = JSON.stringify(snapshot, null, 2);
}

async function loadClientDetails(clientUid) {
  const snapshots = await apiGet(`/api/clients/${clientUid}/snapshots?limit=100`);
  document.getElementById("detailsTitle").textContent = `Client-Details: ${clientUid}`;
  renderSnapshotDetails(snapshots[0]);
  renderHistory(snapshots);
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
      <td class="px-3 py-2">${row.hostname}</td>
      <td class="px-3 py-2 font-mono text-xs">${row.client_uid}</td>
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
      <td class="px-3 py-2">${alert.client_uid}</td>
      <td class="px-3 py-2">${alert.rule_name}</td>
      <td class="px-3 py-2">${fmt(alert.metric_value, 2)}</td>
      <td class="px-3 py-2">${alert.message}</td>
    `;
    tbody.appendChild(tr);
  });
}

function buildSetupCommands(serverOrigin, token) {
  return `python3 -m venv .venv
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
  document.getElementById("setupCommands").textContent = buildSetupCommands(
    tokenPayload.server_origin,
    tokenPayload.token
  );
  showOnboardingStatus("Neuer Client-Token wurde erfolgreich generiert.");
}

async function refreshAll() {
  showError("");
  const clients = await apiGet("/api/clients");
  renderClients(clients);
  await loadAlerts();
  if (selectedClientUid) {
    await loadClientDetails(selectedClientUid);
  } else if (clients.length > 0) {
    selectedClientUid = clients[0].client_uid;
    await loadClientDetails(selectedClientUid);
  } else {
    document.getElementById("snapshotDetails").textContent = "Noch keine Client-Daten vorhanden";
  }
}

document.getElementById("refreshBtn").addEventListener("click", async () => {
  try {
    await refreshAll();
  } catch (error) {
    showError(error.message);
  }
});

document.getElementById("openOnboardingBtn").addEventListener("click", async () => {
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
    await navigator.clipboard.writeText(onboardingTokenValue);
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

refreshAll().catch((error) => showError(error.message));
