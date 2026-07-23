const state = {
  data: null,
  selected: new Set(),
  category: "all",
  query: "",
  submitting: false,
};

const elements = {
  hitCount: document.querySelector("#hit-count"),
  answeredCount: document.querySelector("#answered-count"),
  hitRanks: document.querySelector("#hit-ranks"),
  search: document.querySelector("#menu-search"),
  tabs: document.querySelector("#category-tabs"),
  list: document.querySelector("#menu-list"),
  status: document.querySelector("#status-message"),
  selectionBar: document.querySelector("#selection-bar"),
  selectedCount: document.querySelector("#selected-count"),
  submit: document.querySelector("#submit-selection"),
  dialog: document.querySelector("#confirm-dialog"),
  confirmList: document.querySelector("#confirm-menu-list"),
  confirmSubmit: document.querySelector("#confirm-submit"),
  overlay: document.querySelector("#reveal-overlay"),
  revealMenu: document.querySelector("#reveal-menu"),
  revealRank: document.querySelector("#reveal-rank"),
};

const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const wait = (ms) => new Promise((resolve) => window.setTimeout(resolve, reducedMotion ? 30 : ms));

async function fetchState({silent = false} = {}) {
  try {
    const response = await fetch("/api/state", {cache: "no-store"});
    if (!response.ok) throw new Error(`state request failed: ${response.status}`);
    state.data = await response.json();
    for (const category of state.data.categories) {
      for (const menu of category.menus) {
        if (menu.answered) state.selected.delete(menu.id);
      }
    }
    render();
    if (!silent) elements.status.textContent = "最新の状態を読み込みました。";
  } catch (error) {
    console.error(error);
    elements.status.textContent = "状態を取得できませんでした。しばらくして再読み込みしてください。";
  }
}

function render() {
  if (!state.data) return;
  renderSummary();
  renderTabs();
  renderMenus();
  renderSelection();
}

function renderSummary() {
  const summary = state.data.summary;
  elements.hitCount.textContent = `${summary.top10HitCount} / 10`;
  elements.answeredCount.textContent = `${summary.answeredCount} / ${summary.totalCount}`;
  elements.hitRanks.textContent = summary.hitRanks.length
    ? summary.hitRanks.map((rank) => `${rank}位`).join("・")
    : "まだなし";
}

function renderTabs() {
  const tabs = [{id: "all", name: "すべて"}, ...state.data.categories.map((category) => ({
    id: String(category.id), name: category.name,
  }))];
  elements.tabs.replaceChildren(...tabs.map((tab) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = tab.name;
    button.setAttribute("role", "tab");
    button.setAttribute("aria-selected", String(state.category === tab.id));
    button.addEventListener("click", () => { state.category = tab.id; render(); });
    return button;
  }));
}

function visibleMenu(menu, categoryId) {
  const categoryMatches = state.category === "all" || state.category === String(categoryId);
  const queryMatches = menu.name.toLocaleLowerCase("ja").includes(state.query);
  return categoryMatches && queryMatches;
}

function renderMenus() {
  const sections = [];
  for (const category of state.data.categories) {
    const menus = category.menus.filter((menu) => visibleMenu(menu, category.id));
    if (!menus.length) continue;
    const section = document.createElement("section");
    section.className = "menu-category";
    const heading = document.createElement("h2");
    heading.textContent = category.name;
    const grid = document.createElement("div");
    grid.className = "menu-grid";
    grid.replaceChildren(...menus.map(menuCard));
    section.append(heading, grid);
    sections.push(section);
  }
  if (!sections.length) {
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent = "条件に一致するメニューがありません。";
    elements.list.replaceChildren(empty);
    return;
  }
  elements.list.replaceChildren(...sections);
}

function menuCard(menu) {
  const label = document.createElement("label");
  label.className = `menu-card${menu.answered ? " answered" : ""}${state.selected.has(menu.id) ? " selected" : ""}`;
  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.checked = state.selected.has(menu.id);
  checkbox.disabled = menu.answered || state.submitting;
  checkbox.addEventListener("change", () => {
    checkbox.checked ? state.selected.add(menu.id) : state.selected.delete(menu.id);
    render();
  });
  const name = document.createElement("span");
  name.className = "menu-name";
  name.textContent = menu.name;
  label.append(checkbox, name);
  if (menu.answered) {
    const badge = document.createElement("span");
    badge.className = `rank-badge${menu.rank <= 10 ? " top10" : ""}`;
    badge.textContent = `${menu.rank}位`;
    label.append(badge);
  }
  return label;
}

function renderSelection() {
  const count = state.selected.size;
  elements.selectionBar.hidden = count === 0;
  elements.selectedCount.textContent = String(count);
  elements.submit.disabled = state.submitting;
}

function selectedMenus() {
  const byId = new Map();
  for (const category of state.data.categories) {
    for (const menu of category.menus) byId.set(menu.id, menu);
  }
  return [...state.selected].map((id) => byId.get(id)).filter(Boolean);
}

function openConfirmation() {
  const menus = selectedMenus();
  elements.confirmList.replaceChildren(...menus.map((menu) => {
    const item = document.createElement("li");
    item.textContent = menu.name;
    return item;
  }));
  elements.dialog.showModal();
}

async function submitSelection() {
  if (!state.selected.size || state.submitting) return;
  state.submitting = true;
  renderSelection();
  try {
    const response = await fetch("/api/guesses", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({menu_ids: [...state.selected]}),
    });
    if (!response.ok) throw new Error(`guess request failed: ${response.status}`);
    const payload = await response.json();
    elements.dialog.close();
    const newResults = payload.results.filter((result) => result.newlyAnswered);
    if (newResults.length) await playRevealSequence(newResults);
    state.selected.clear();
    await fetchState({silent: true});
    elements.status.textContent = newResults.length
      ? `${newResults.length}件の順位を公開しました。`
      : "選択したメニューは既に回答済みでした。";
  } catch (error) {
    console.error(error);
    elements.status.textContent = "順位を確認できませんでした。もう一度送信してください。";
  } finally {
    state.submitting = false;
    renderSelection();
  }
}

async function playRevealSequence(results) {
  elements.overlay.hidden = false;
  for (const result of results) {
    elements.overlay.className = "reveal-overlay phase-name";
    elements.overlay.classList.toggle("is-top10", result.isTop10);
    elements.revealMenu.textContent = result.menuName;
    elements.revealRank.textContent = "";
    await wait(1500);
    elements.overlay.className = `reveal-overlay phase-fade${result.isTop10 ? " is-top10" : ""}`;
    await wait(550);
    elements.revealMenu.textContent = "";
    elements.revealRank.textContent = `${result.rank}位`;
    elements.overlay.className = `reveal-overlay phase-rank${result.isTop10 ? " is-top10" : ""}`;
    await wait(result.isTop10 ? 2300 : 1800);
  }
  elements.overlay.hidden = true;
  elements.overlay.className = "reveal-overlay";
}

elements.search.addEventListener("input", (event) => {
  state.query = event.target.value.trim().toLocaleLowerCase("ja");
  renderMenus();
});
elements.submit.addEventListener("click", openConfirmation);
elements.dialog.addEventListener("close", () => {
  if (elements.dialog.returnValue === "default") submitSelection();
});
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible" && !state.submitting) fetchState({silent: true});
});

fetchState();
const pollInterval = Number(document.body.dataset.pollInterval || 10000);
window.setInterval(() => {
  if (!state.submitting && elements.overlay.hidden) fetchState({silent: true});
}, pollInterval);
