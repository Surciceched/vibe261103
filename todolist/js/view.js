const $ = (id) => document.getElementById(id);

const THEME_LABELS = { system: "시스템 테마", light: "라이트 테마", dark: "다크 테마" };
const TOAST_DURATION_MS = 5000;

const el = {
  date: $("today-date"),
  theme: $("theme-toggle"),
  progress: $("progress"),
  progressBar: $("progress-bar"),
  progressFill: $("progress-fill"),
  progressLabel: $("progress-label"),
  saveWarning: $("save-warning"),
  carryover: $("carryover"),
  carryoverMessage: $("carryover-message"),
  carryoverAccept: $("carryover-accept"),
  carryoverDiscard: $("carryover-discard"),
  addForm: $("add-form"),
  addInput: $("add-input"),
  emptyState: $("empty-state"),
  allDone: $("all-done"),
  activeList: $("active-list"),
  completedSection: $("completed-section"),
  completedToggle: $("completed-toggle"),
  completedCount: $("completed-count"),
  completedList: $("completed-list"),
  clearCompleted: $("clear-completed"),
  toast: $("toast"),
  toastMessage: $("toast-message"),
  toastUndo: $("toast-undo"),
  live: $("live"),
  template: $("todo-template"),
};

const itemsById = new Map();
let isRendering = false;
let toastTimer = null;
let toastUndoCallback = null;
let dragId = null;
let dropIndex = null;

const control = (li, role) => li.querySelector(`[data-role="${role}"]`);
const isShown = (element) => element.isConnected && element.getClientRects().length > 0;

function createItem(todo) {
  const li = el.template.content.firstElementChild.cloneNode(true);
  li.dataset.id = todo.id;
  itemsById.set(todo.id, li);
  return li;
}

function updateItem(li, todo, { index, total, editing }) {
  const movable = !todo.completed && total > 1;
  const text = li.querySelector(".todo__text");
  li.classList.toggle("todo--done", todo.completed);
  li.classList.toggle("todo--static", !movable);

  text.textContent = todo.text;
  const checkbox = control(li, "toggle");
  checkbox.checked = todo.completed;
  checkbox.setAttribute("aria-label", `${todo.text} 완료`);

  const up = control(li, "up");
  const down = control(li, "down");
  up.hidden = !movable;
  down.hidden = !movable;
  up.setAttribute("aria-disabled", String(index === 0));
  down.setAttribute("aria-disabled", String(index === total - 1));
  up.setAttribute("aria-label", `${todo.text} 위로 이동`);
  down.setAttribute("aria-label", `${todo.text} 아래로 이동`);
  control(li, "edit").setAttribute("aria-label", `${todo.text} 수정`);
  control(li, "delete").setAttribute("aria-label", `${todo.text} 삭제`);

  // 다른 탭에서 변경이 들어와도 입력 중인 내용은 유지한다.
  const input = control(li, "edit-input");
  if (editing && !li.classList.contains("todo--editing")) input.value = todo.text;
  li.classList.toggle("todo--editing", editing);
  input.hidden = !editing;
  text.hidden = editing;
}

// 항목을 재사용하고 위치가 다를 때만 옮겨, 클릭 중인 요소와 포커스가 사라지지 않게 한다.
function syncList(list, todos, editingId) {
  todos.forEach((todo, index) => {
    const li = itemsById.get(todo.id) ?? createItem(todo);
    updateItem(li, todo, { index, total: todos.length, editing: todo.id === editingId });
    const current = list.children[index];
    if (current !== li) list.insertBefore(li, current ?? null);
  });
  while (list.children.length > todos.length) list.lastElementChild.remove();
}

function pruneItems() {
  for (const [id, li] of itemsById) {
    if (!li.isConnected) itemsById.delete(id);
  }
}

function captureFocus() {
  const active = document.activeElement;
  if (!active || active === document.body) return null;
  return { element: active, id: active.closest(".todo")?.dataset.id, role: active.dataset.role };
}

function applyFocus(target) {
  const li = target === "add" ? null : itemsById.get(target.id);
  const element = li && control(li, target.role);
  if (!element || !isShown(element)) {
    el.addInput.focus();
    return;
  }
  element.focus();
  if (target.role === "edit-input") element.setSelectionRange(element.value.length, element.value.length);
}

function restoreFocus(previous) {
  if (!previous) return;
  const stillFocused = document.activeElement === previous.element && isShown(previous.element);
  if (stillFocused) return;
  if (previous.id && previous.role) applyFocus({ id: previous.id, role: previous.role });
  else applyFocus("add");
}

export function render(vm, focusTarget = null) {
  isRendering = true;
  const previousFocus = captureFocus();

  el.date.textContent = vm.dateLabel;
  el.theme.textContent = THEME_LABELS[vm.theme];
  el.theme.setAttribute("aria-label", `${THEME_LABELS[vm.theme]} 사용 중, 눌러서 변경`);
  document.documentElement.dataset.theme = vm.theme;

  const doneCount = vm.completed.length;
  const total = vm.active.length + doneCount;
  el.progress.hidden = total === 0;
  el.progressBar.setAttribute("aria-valuemax", String(total));
  el.progressBar.setAttribute("aria-valuenow", String(doneCount));
  el.progressFill.style.width = total ? `${(doneCount / total) * 100}%` : "0";
  el.progressLabel.textContent = `${doneCount} / ${total} 완료`;

  el.saveWarning.hidden = !vm.saveFailed;
  el.carryover.hidden = !vm.carryoverMessage;
  el.carryoverMessage.textContent = vm.carryoverMessage ?? "";
  el.emptyState.hidden = total !== 0;
  el.allDone.hidden = total === 0 || vm.active.length !== 0;

  syncList(el.activeList, vm.active, vm.editingId);
  syncList(el.completedList, vm.collapsed ? [] : vm.completed, vm.editingId);
  pruneItems();

  el.completedSection.hidden = doneCount === 0;
  el.completedCount.textContent = `완료 ${doneCount}개`;
  el.completedToggle.setAttribute("aria-expanded", String(!vm.collapsed));

  if (focusTarget) applyFocus(focusTarget);
  else restoreFocus(previousFocus);
  isRendering = false;
}

export function announce(message) {
  el.live.textContent = message;
}

function startToastTimer() {
  clearTimeout(toastTimer);
  toastTimer = setTimeout(hideToast, TOAST_DURATION_MS);
}

export function hideToast() {
  clearTimeout(toastTimer);
  toastUndoCallback = null;
  el.toast.hidden = true;
}

export function showToast(message, undo = null) {
  toastUndoCallback = undo;
  el.toastMessage.textContent = message;
  el.toastUndo.hidden = !undo;
  el.toast.hidden = false;
  startToastTimer();
}

function clearDropIndicators() {
  for (const li of el.activeList.children) {
    li.classList.remove("todo--drop-before", "todo--drop-after");
  }
}

function bindList(list, handlers) {
  list.addEventListener("change", (event) => {
    if (event.target.dataset.role === "toggle") {
      handlers.onToggle(event.target.closest(".todo").dataset.id);
    }
  });

  list.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-role]");
    if (!button || button.getAttribute("aria-disabled") === "true") return;
    const id = button.closest(".todo").dataset.id;
    if (button.dataset.role === "edit") handlers.onEditStart(id);
    if (button.dataset.role === "delete") handlers.onDelete(id);
    if (button.dataset.role === "up") handlers.onMove(id, -1);
    if (button.dataset.role === "down") handlers.onMove(id, 1);
  });

  list.addEventListener("dblclick", (event) => {
    if (event.target.closest(".todo__text")) handlers.onEditStart(event.target.closest(".todo").dataset.id);
  });

  list.addEventListener("keydown", (event) => {
    // 한글 조합 중의 Enter와 Esc는 조합을 끝내는 입력이므로 무시한다.
    if (event.target.dataset.role !== "edit-input" || event.isComposing) return;
    const id = event.target.closest(".todo").dataset.id;
    if (event.key === "Enter") {
      event.preventDefault();
      handlers.onEditCommit(id, event.target.value, true);
    } else if (event.key === "Escape") {
      handlers.onEditCancel(id);
    }
  });

  list.addEventListener("focusout", (event) => {
    if (isRendering || event.target.dataset.role !== "edit-input") return;
    handlers.onEditCommit(event.target.closest(".todo").dataset.id, event.target.value, false);
  });
}

function bindDragAndDrop(handlers) {
  const list = el.activeList;

  list.addEventListener("dragstart", (event) => {
    const handle = event.target.closest?.(".todo__handle");
    if (!handle) return;
    const li = handle.closest(".todo");
    dragId = li.dataset.id;
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", dragId);
    event.dataTransfer.setDragImage(li, 16, 24);
    li.classList.add("todo--dragging");
  });

  list.addEventListener("dragover", (event) => {
    if (!dragId) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";

    const others = [...list.children].filter((li) => li.dataset.id !== dragId);
    const before = others.findIndex((li) => {
      const rect = li.getBoundingClientRect();
      return event.clientY < rect.top + rect.height / 2;
    });
    dropIndex = before < 0 ? others.length : before;

    clearDropIndicators();
    if (others[dropIndex]) others[dropIndex].classList.add("todo--drop-before");
    else others.at(-1)?.classList.add("todo--drop-after");
  });

  list.addEventListener("dragleave", (event) => {
    if (list.contains(event.relatedTarget)) return;
    dropIndex = null;
    clearDropIndicators();
  });

  list.addEventListener("drop", (event) => {
    if (!dragId) return;
    event.preventDefault();
    if (dropIndex !== null) handlers.onReorder(dragId, dropIndex);
  });

  list.addEventListener("dragend", () => {
    itemsById.get(dragId)?.classList.remove("todo--dragging");
    clearDropIndicators();
    dragId = null;
    dropIndex = null;
  });
}

function bindToast() {
  el.toastUndo.addEventListener("click", () => {
    const undo = toastUndoCallback;
    hideToast();
    undo?.();
  });

  // 키보드나 마우스로 토스트를 조작하는 동안에는 사라지지 않게 한다.
  const pause = () => clearTimeout(toastTimer);
  const resume = () => {
    if (!el.toast.hidden && !el.toast.matches(":hover, :focus-within")) startToastTimer();
  };
  el.toast.addEventListener("mouseenter", pause);
  el.toast.addEventListener("focusin", pause);
  el.toast.addEventListener("mouseleave", resume);
  el.toast.addEventListener("focusout", () => setTimeout(resume));
}

export function bindEvents(handlers) {
  // 한글 조합 중의 Enter는 글자를 확정하는 입력이므로 제출로 처리하지 않는다.
  el.addInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && event.isComposing) event.preventDefault();
  });

  el.addForm.addEventListener("submit", (event) => {
    event.preventDefault();
    if (handlers.onAdd(el.addInput.value)) el.addInput.value = "";
    el.addInput.focus();
  });

  bindList(el.activeList, handlers);
  bindList(el.completedList, handlers);
  bindDragAndDrop(handlers);
  bindToast();

  el.theme.addEventListener("click", handlers.onThemeCycle);
  el.carryoverAccept.addEventListener("click", handlers.onCarryoverAccept);
  el.carryoverDiscard.addEventListener("click", handlers.onCarryoverDiscard);
  el.completedToggle.addEventListener("click", handlers.onCollapseToggle);
  el.clearCompleted.addEventListener("click", handlers.onClearCompleted);
}
