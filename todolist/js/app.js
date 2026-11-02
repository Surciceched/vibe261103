import { formatDate, previousDay, todayString } from "./date.js";
import * as storage from "./storage.js";
import * as store from "./store.js";
import * as view from "./view.js";

const DATE_CHECK_INTERVAL_MS = 60_000;
const THEME_ORDER = ["system", "light", "dark"];

const state = {
  data: null,
  today: todayString(),
  editingId: null,
  saveFailed: false,
};

function newId() {
  // randomUUID는 HTTPS와 localhost에서만 제공되므로, 사설망 주소 접속에 대비해 대체값을 둔다.
  return crypto.randomUUID?.() ?? `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
}

function carryoverMessage() {
  const carried = store.selectCarryover(state.data, state.today);
  if (carried.length === 0) return null;
  const yesterday = previousDay(state.today);
  const label = carried.every((todo) => todo.date === yesterday) ? "어제" : "지난번에";
  return `${label} 못 끝낸 일 ${carried.length}개가 있어요`;
}

function renderApp(focusTarget) {
  const { active, completed } = store.selectDay(state.data, state.today);
  view.render(
    {
      dateLabel: formatDate(state.today),
      active,
      completed,
      collapsed: state.data.settings.completedCollapsed,
      theme: state.data.settings.theme,
      editingId: state.editingId,
      carryoverMessage: carryoverMessage(),
      saveFailed: state.saveFailed,
    },
    focusTarget,
  );
}

function persist(nextData) {
  state.data = nextData;
  state.saveFailed = !storage.save(nextData);
}

function commit(nextData, focusTarget) {
  if (nextData !== state.data) persist(nextData);
  renderApp(focusTarget);
}

function offerUndo(message, removed) {
  view.showToast(message, () => {
    commit(store.restoreTodos(state.data, removed), "add");
  });
}

function neighborFocus(id) {
  const { active, completed } = store.selectDay(state.data, state.today);
  const list = active.some((todo) => todo.id === id) ? active : completed;
  const index = list.findIndex((todo) => todo.id === id);
  const neighbor = list[index + 1] ?? list[index - 1];
  return neighbor ? { id: neighbor.id, role: "delete" } : "add";
}

function applyLoaded({ data, status }) {
  state.data = data;
  if (status === "unavailable") state.saveFailed = true;
  if (status === "corrupted") view.showToast("저장된 데이터를 읽지 못해 새로 시작해요");
}

function cleanUpOldCompleted() {
  const next = store.purgeOldCompleted(state.data, state.today);
  if (next !== state.data) persist(next);
}

function checkDateChange() {
  const today = todayString();
  if (today === state.today) return;
  state.today = today;
  state.editingId = null;
  cleanUpOldCompleted();
  renderApp();
}

const handlers = {
  onAdd(rawText) {
    checkDateChange();
    const next = store.addTodo(state.data, rawText, {
      id: newId(),
      today: state.today,
      now: new Date().toISOString(),
    });
    if (next === state.data) return false;
    commit(next);
    view.announce("할일을 추가했어요");
    return true;
  },

  onToggle(id) {
    commit(store.toggleTodo(state.data, id, new Date().toISOString()));
  },

  onEditStart(id) {
    state.editingId = id;
    renderApp({ id, role: "edit-input" });
  },

  onEditCommit(id, value, keepFocus) {
    if (state.editingId !== id) return;
    state.editingId = null;
    commit(store.editTodo(state.data, id, value), keepFocus ? { id, role: "edit" } : null);
  },

  onEditCancel(id) {
    if (state.editingId !== id) return;
    state.editingId = null;
    renderApp({ id, role: "edit" });
  },

  onDelete(id) {
    const removed = state.data.todos.filter((todo) => todo.id === id);
    const focusTarget = neighborFocus(id);
    commit(store.removeTodos(state.data, [id]), focusTarget);
    offerUndo("할일을 삭제했어요", removed);
  },

  onMove(id, delta) {
    const { active } = store.selectDay(state.data, state.today);
    const index = active.findIndex((todo) => todo.id === id);
    commit(store.reorderActive(state.data, id, index + delta, state.today));
    view.announce(`${index + delta + 1}번째로 옮겼어요`);
  },

  onReorder(id, targetIndex) {
    commit(store.reorderActive(state.data, id, targetIndex, state.today));
  },

  onCarryoverAccept() {
    commit(store.carryOverToToday(state.data, state.today), "add");
  },

  onCarryoverDiscard() {
    const removed = store.selectCarryover(state.data, state.today);
    commit(store.removeTodos(state.data, removed.map((todo) => todo.id)), "add");
    offerUndo(`못 끝낸 일 ${removed.length}개를 버렸어요`, removed);
  },

  onCollapseToggle() {
    const collapsed = !state.data.settings.completedCollapsed;
    commit(store.updateSettings(state.data, { completedCollapsed: collapsed }));
  },

  onClearCompleted() {
    const { completed } = store.selectDay(state.data, state.today);
    commit(store.removeTodos(state.data, completed.map((todo) => todo.id)), "add");
    offerUndo(`완료 항목 ${completed.length}개를 지웠어요`, completed);
  },

  onThemeCycle() {
    const current = THEME_ORDER.indexOf(state.data.settings.theme);
    const theme = THEME_ORDER[(current + 1) % THEME_ORDER.length];
    commit(store.updateSettings(state.data, { theme }));
  },
};

function syncFromOtherTab() {
  applyLoaded(storage.load());
  if (!state.data.todos.some((todo) => todo.id === state.editingId)) state.editingId = null;
  renderApp();
}

function init() {
  applyLoaded(storage.load());
  cleanUpOldCompleted();
  view.bindEvents(handlers);
  storage.onExternalChange(syncFromOtherTab);

  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) checkDateChange();
  });
  window.addEventListener("focus", checkDateChange);
  setInterval(checkDateChange, DATE_CHECK_INTERVAL_MS);

  renderApp("add");
}

init();
