const adminState = {menus: [], categories: [], editing: null, pending: null};
const el = {
  rows: document.querySelector("#menu-rows"), search: document.querySelector("#search"),
  status: document.querySelector("#status"), add: document.querySelector("#add-menu"),
  editDialog: document.querySelector("#edit-dialog"), editForm: document.querySelector("#edit-form"),
  title: document.querySelector("#dialog-title"), menuId: document.querySelector("#menu-id"),
  name: document.querySelector("#name"), category: document.querySelector("#category"),
  rank: document.querySelector("#rank"), displayOrder: document.querySelector("#display-order"),
  active: document.querySelector("#active"), answered: document.querySelector("#answered"),
  categories: document.querySelector("#categories"), cancel: document.querySelector("#cancel"),
  confirmDialog: document.querySelector("#confirm-dialog"), summary: document.querySelector("#change-summary"),
};

async function load() {
  const response = await fetch("/api/admin/state", {cache: "no-store"});
  if (!response.ok) throw new Error("管理データを取得できませんでした");
  const data = await response.json();
  adminState.menus = data.menus;
  adminState.categories = data.categories;
  render();
}

function render() {
  const query = el.search.value.trim().toLocaleLowerCase("ja");
  const menus = adminState.menus.filter((menu) => menu.name.toLocaleLowerCase("ja").includes(query));
  el.rows.replaceChildren(...menus.map((menu) => {
    const tr = document.createElement("tr");
    if (!menu.is_active) tr.classList.add("inactive");
    const values = [menu.rank, menu.name, menu.category_name];
    for (const value of values) { const td = document.createElement("td"); td.textContent = value; tr.append(td); }
    const active = document.createElement("td"); active.textContent = menu.is_active ? "公開" : "非表示"; tr.append(active);
    const answered = document.createElement("td");
    const badge = document.createElement("span"); badge.className = `badge${menu.answered ? " answered" : ""}`;
    badge.textContent = menu.answered ? "回答済み" : "未回答"; answered.append(badge); tr.append(answered);
    const action = document.createElement("td"); const button = document.createElement("button");
    button.type = "button"; button.textContent = "編集"; button.addEventListener("click", () => openEdit(menu));
    action.append(button); tr.append(action); return tr;
  }));
  el.categories.replaceChildren(...adminState.categories.map((category) => {
    const option = document.createElement("option"); option.value = category.name; return option;
  }));
}

function openEdit(menu = null) {
  adminState.editing = menu;
  el.title.textContent = menu ? "メニューを編集" : "メニューを追加";
  el.menuId.value = menu?.id || "";
  el.name.value = menu?.name || "";
  el.category.value = menu?.category_name || "";
  el.rank.value = menu?.rank || "";
  el.displayOrder.value = menu?.display_order ?? 0;
  el.active.checked = menu?.is_active ?? true;
  el.answered.checked = menu?.answered ?? false;
  el.editDialog.showModal();
}

function formPayload() {
  return {
    name: el.name.value.trim(), category_name: el.category.value.trim(), rank: Number(el.rank.value),
    display_order: Number(el.displayOrder.value), is_active: el.active.checked, answered: el.answered.checked,
  };
}

el.editForm.addEventListener("submit", (event) => {
  event.preventDefault();
  adminState.pending = formPayload();
  el.summary.textContent = [
    `メニュー: ${adminState.pending.name}`, `カテゴリ: ${adminState.pending.category_name}`,
    `順位: ${adminState.pending.rank}位`, `表示: ${adminState.pending.is_active ? "公開" : "非表示"}`,
    `回答: ${adminState.pending.answered ? "回答済み" : "未回答"}`,
  ].join("\n");
  el.confirmDialog.showModal();
});

el.confirmDialog.addEventListener("close", async () => {
  if (el.confirmDialog.returnValue !== "save" || !adminState.pending) return;
  try {
    const editingId = el.menuId.value;
    const response = await fetch(editingId ? `/api/admin/menus/${editingId}` : "/api/admin/menus", {
      method: editingId ? "PATCH" : "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify(adminState.pending),
    });
    if (!response.ok) { const detail = await response.json(); throw new Error(detail.detail || "保存に失敗しました"); }
    el.editDialog.close(); el.status.textContent = "変更を保存しました。"; await load();
  } catch (error) { el.status.textContent = error.message; }
});

el.search.addEventListener("input", render);
el.add.addEventListener("click", () => openEdit());
el.cancel.addEventListener("click", () => el.editDialog.close());
load().catch((error) => { el.status.textContent = error.message; });
