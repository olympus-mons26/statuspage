const themeToggle = document.querySelector("#theme-toggle");
const themeLabel = document.querySelector("#theme-label");
const themeIcon = document.querySelector("#theme-icon");
const themeColor = document.querySelector('meta[name="theme-color"]');
const siteList = document.querySelector("#site-status");
const updatedAt = document.querySelector("#updated-at");
const loadError = document.querySelector("#load-error");
const refreshIntervalMs = 60_000;

function readTheme() {
  try {
    const savedTheme = localStorage.getItem("status-theme");
    if (savedTheme === "light" || savedTheme === "dark") {
      return savedTheme;
    }
  } catch (error) {
    console.warn("Could not read the saved theme preference:", error);
  }

  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function saveTheme(theme) {
  try {
    localStorage.setItem("status-theme", theme);
  } catch (error) {
    console.warn("Could not save the theme preference:", error);
  }
}

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  themeColor.content = theme === "dark" ? "#121211" : "#faf8f4";
  themeToggle.setAttribute("aria-pressed", String(theme === "dark"));
  themeLabel.textContent = theme === "dark" ? "Light mode" : "Dark mode";
  themeIcon.textContent = theme === "dark" ? "☀" : "☾";
}

themeToggle.addEventListener("click", () => {
  const nextTheme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  saveTheme(nextTheme);
  applyTheme(nextTheme);
});

applyTheme(readTheme());

function formatDate(value) {
  if (!value) {
    return "Not checked yet";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Not checked yet";
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function makeSiteRow(site) {
  const item = document.createElement("li");
  const row = document.createElement("article");
  row.className = "site-row";

  const identity = document.createElement("div");
  identity.className = "service-name";

  const icon = document.createElement("span");
  icon.className = "service-icon";
  icon.setAttribute("aria-hidden", "true");
  icon.textContent = site.name.trim().charAt(0).toUpperCase() || "?";

  const details = document.createElement("div");
  details.className = "service-details";

  const name = document.createElement("h3");
  name.textContent = site.name;

  const link = document.createElement("a");
  link.href = site.url;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  link.textContent = site.url;
  link.setAttribute("aria-label", `${site.name} website`);

  details.append(name, link);
  identity.append(icon, details);

  const result = document.createElement("div");
  result.className = "service-result";

  const status = document.createElement("span");
  status.className = "status-badge";
  const knownStatuses = new Set(["up", "down"]);
  const statusKey = knownStatuses.has(site.status) ? site.status : "unknown";
  status.dataset.status = statusKey;
  status.textContent = statusKey === "up"
    ? "Running..."
    : statusKey === "down"
      ? "Not working :("
      : "Waiting for check";

  const checkTime = document.createElement("p");
  checkTime.className = "check-time";
  checkTime.textContent = site.checkedAt ? `Checked ${formatDate(site.checkedAt)}` : "Awaiting first check";

  result.append(status, checkTime);
  row.append(identity, result);
  item.append(row);
  return item;
}

function displaySites(data) {
  if (!Array.isArray(data.sites)) {
    throw new Error("The status response has an invalid format.");
  }

  siteList.replaceChildren();
  if (data.sites.length === 0) {
    const empty = document.createElement("li");
    empty.className = "empty-state";
    empty.textContent = "No websites are being monitored yet.";
    siteList.append(empty);
  } else {
    for (const site of data.sites) {
      if (typeof site.name !== "string" || typeof site.url !== "string") {
        continue;
      }
      siteList.append(makeSiteRow(site));
    }
  }

  updatedAt.textContent = data.generatedAt
    ? `Status last updated ${formatDate(data.generatedAt)}`
    : "Waiting for the first check…";

  const generatedAt = Date.parse(data.generatedAt);
  if (Number.isFinite(generatedAt) && Date.now() - generatedAt > 30 * 60_000) {
    loadError.hidden = false;
    loadError.textContent = "The latest scheduled check is delayed. These results may be out of date.";
  } else {
    loadError.hidden = true;
    loadError.textContent = "";
  }
}

async function refreshStatus() {
  siteList.setAttribute("aria-busy", "true");
  try {
    const response = await fetch(`./status.json?refresh=${Date.now()}`, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`Status request failed with HTTP ${response.status}.`);
    }
    displaySites(await response.json());
    loadError.hidden = loadError.textContent === "";
  } catch (error) {
    loadError.hidden = false;
    loadError.textContent = "Unable to load the latest status. Please try again shortly.";
    if (siteList.children.length === 1 && siteList.firstElementChild.classList.contains("loading-state")) {
      siteList.firstElementChild.textContent = "Status information is temporarily unavailable.";
    }
    console.error("Could not refresh status:", error);
  } finally {
    siteList.setAttribute("aria-busy", "false");
  }
}

async function loadSiteLinks() {
  try {
    const response = await fetch("./site-config.json", { cache: "no-cache" });
    if (!response.ok) {
      throw new Error(`Configuration request failed with HTTP ${response.status}.`);
    }
    const config = await response.json();
    if (typeof config.contactUrl === "string") {
      document.querySelector("#contact-link").href = config.contactUrl;
    }
    if (typeof config.repositoryUrl === "string") {
      document.querySelector("#repository-link").href = config.repositoryUrl;
    }
  } catch (error) {
    console.error("Could not load page links:", error);
  }
}

refreshStatus();
loadSiteLinks();
window.setInterval(refreshStatus, refreshIntervalMs);
