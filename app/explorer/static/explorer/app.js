// Page behaviour without a framework: settings in the menu, and the filter form.

const STORE = "toxage-";

function load(key) {
  try { return localStorage.getItem(STORE + key) || ""; } catch { return ""; }
}

function save(key, value) {
  try {
    if (value) localStorage.setItem(STORE + key, value);
    else localStorage.removeItem(STORE + key);
  } catch { /* storage blocked: the setting lasts for this page only */ }
}

function apply(key, value) {
  if (value) document.documentElement.dataset[key] = value;
  else delete document.documentElement.dataset[key];
}

for (const set of document.querySelectorAll("[data-setting]")) {
  const key = set.dataset.setting;
  const current = load(key);
  for (const input of set.querySelectorAll("input")) {
    input.checked = input.value === current;
    input.addEventListener("change", () => { save(key, input.value); apply(key, input.value); });
  }
}

// Close the menu on a click outside it.
document.addEventListener("click", (event) => {
  const menu = document.querySelector("details.menu[open]");
  // A click in the hint of a tour does not count; its button may be gone by now.
  const tour = event.target.closest(".tour") || !event.target.isConnected;
  if (menu && !menu.contains(event.target) && !tour) menu.open = false;
});

// Filter form: leave empty fields out of the address, apply on change.
const filters = document.getElementById("filters");
if (filters) {
  filters.addEventListener("submit", () => {
    for (const el of filters.elements) if (el.name && el.value === "") el.disabled = true;
  });
  filters.addEventListener("change", () => filters.requestSubmit());
}

// Scenario choice: apply on change.
const scenario = document.getElementById("scenario");
if (scenario) scenario.addEventListener("change", () => scenario.requestSubmit());

// Ask before deleting or resetting.
document.addEventListener("submit", (event) => {
  const question = event.submitter?.dataset.confirmButton || event.target.dataset.confirm;
  // The demo answers for the user.
  if (document.documentElement.dataset.tourAuto === "1") return;
  if (question && !window.confirm(question)) event.preventDefault();
});
