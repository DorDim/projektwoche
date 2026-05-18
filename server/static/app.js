let selectedClientUid = null;
let historyChart = null;

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

function renderClients(clients) {
  const tbody = document.querySelector("#clientsTable tbody");
  tbody.innerHTML = "";

  clients.forEach((client) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><input type="checkbox" data-uid="${client.client_uid}" class="compare-check"/></td>
      <td>${client.hostname}</td>
      <td>${client.client_uid}</td>
      <td class="status-${client.status}">${client.status}</td>
      <td>${fmt(client.latest_snapshot?.cpu_threads, 0)}</td>
      <td>${fmt(client.latest_snapshot?.ram_total_mb, 0)}</td>
      <td>${fmt(client.latest_snapshot?.min_disk_free_percent, 2)}</td>
      <td>${new Date(client.last_seen).toLocaleString()}</td>
    `;
    tr.addEventListener("click", (event) => {
      if (event.target && event.target.classList.contains("compare-check")) {
        return;
      }
      selectedClientUid = client.client_uid;
      loadClientDetails(client.client_uid);
    });
    tbody.appendChild(tr);
  });

  document.querySelectorAll(".compare-check").forEach((checkbox) => {
    checkbox.addEventListener("change", loadCompare);
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
          label: "CPU-Temperatur (C)",
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
      <td>${row.hostname}</td>
      <td>${row.client_uid}</td>
      <td>${fmt(row.cpu_threads, 0)}</td>
      <td>${fmt(row.ram_total_mb, 0)}</td>
      <td>${fmt(row.min_disk_free_percent, 2)}</td>
      <td>${fmt(row.uptime_seconds, 0)}</td>
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
      <td>${new Date(alert.triggered_at).toLocaleString()}</td>
      <td>${alert.client_uid}</td>
      <td>${alert.rule_name}</td>
      <td>${fmt(alert.metric_value, 2)}</td>
      <td>${alert.message}</td>
    `;
    tbody.appendChild(tr);
  });
}

async function refreshAll() {
  const clients = await apiGet("/api/clients");
  renderClients(clients);
  await loadAlerts();
  if (selectedClientUid) {
    await loadClientDetails(selectedClientUid);
  } else if (clients.length > 0) {
    selectedClientUid = clients[0].client_uid;
    await loadClientDetails(selectedClientUid);
  }
}

document.getElementById("refreshBtn").addEventListener("click", async () => {
  try {
    await refreshAll();
  } catch (error) {
    alert(error.message);
  }
});

refreshAll().catch((error) => alert(error.message));
