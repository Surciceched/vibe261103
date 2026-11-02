// 상태 변경 로직. 모든 함수는 입력을 바꾸지 않고, 내용이 그대로면 같은 객체를 돌려준다.

export const MAX_TEXT_LENGTH = 200;

export function createEmptyData() {
  return {
    version: 1,
    todos: [],
    settings: { theme: "system", completedCollapsed: false },
  };
}

function normalizeText(rawText) {
  const text = rawText.trim();
  return text && text.length <= MAX_TEXT_LENGTH ? text : null;
}

const byOrder = (a, b) => a.order - b.order;

function withTodos(data, todos) {
  return { ...data, todos };
}

function nextOrder(data, today) {
  return data.todos.reduce((max, todo) => (todo.date === today ? Math.max(max, todo.order) : max), -1) + 1;
}

export function selectDay(data, today) {
  const todos = data.todos.filter((todo) => todo.date === today).sort(byOrder);
  return {
    active: todos.filter((todo) => !todo.completed),
    completed: todos.filter((todo) => todo.completed),
  };
}

export function selectCarryover(data, today) {
  return data.todos.filter((todo) => !todo.completed && todo.date < today);
}

export function addTodo(data, rawText, { id, today, now }) {
  const text = normalizeText(rawText);
  if (!text) return data;
  const todo = {
    id,
    text,
    completed: false,
    date: today,
    order: nextOrder(data, today),
    createdAt: now,
    completedAt: null,
  };
  return withTodos(data, [...data.todos, todo]);
}

export function toggleTodo(data, id, now) {
  return withTodos(
    data,
    data.todos.map((todo) =>
      todo.id === id
        ? { ...todo, completed: !todo.completed, completedAt: todo.completed ? null : now }
        : todo,
    ),
  );
}

// 내용을 모두 지우고 저장하면 변경을 취소한다.
export function editTodo(data, id, rawText) {
  const text = normalizeText(rawText);
  const current = data.todos.find((todo) => todo.id === id);
  if (!text || !current || current.text === text) return data;
  return withTodos(
    data,
    data.todos.map((todo) => (todo.id === id ? { ...todo, text } : todo)),
  );
}

export function removeTodos(data, ids) {
  const removed = new Set(ids);
  return withTodos(data, data.todos.filter((todo) => !removed.has(todo.id)));
}

// order 값을 그대로 유지하므로 되돌리면 원래 위치로 돌아간다.
export function restoreTodos(data, todos) {
  const existing = new Set(data.todos.map((todo) => todo.id));
  return withTodos(data, [...data.todos, ...todos.filter((todo) => !existing.has(todo.id))]);
}

// 미완료 항목만 재정렬한다. targetIndex는 옮길 항목을 뺀 미완료 목록 기준의 위치다.
export function reorderActive(data, id, targetIndex, today) {
  const { active, completed } = selectDay(data, today);
  const from = active.findIndex((todo) => todo.id === id);
  if (from < 0) return data;

  const others = active.filter((todo) => todo.id !== id);
  const to = Math.max(0, Math.min(targetIndex, others.length));
  if (to === from) return data;
  others.splice(to, 0, active[from]);

  // 완료 항목과의 상대 순서를 유지하기 위해 미완료 항목이 차지하던 자리 안에서만 바꾼다.
  const day = [...active, ...completed].sort(byOrder);
  let nextActive = 0;
  const orderById = new Map(
    day.map((todo, index) => [todo.completed ? todo.id : others[nextActive++].id, index]),
  );
  return withTodos(
    data,
    data.todos.map((todo) =>
      orderById.has(todo.id) ? { ...todo, order: orderById.get(todo.id) } : todo,
    ),
  );
}

export function carryOverToToday(data, today) {
  const carried = selectCarryover(data, today).sort(
    (a, b) => a.date.localeCompare(b.date) || byOrder(a, b),
  );
  const start = nextOrder(data, today);
  const orderById = new Map(carried.map((todo, index) => [todo.id, start + index]));
  return withTodos(
    data,
    data.todos.map((todo) =>
      orderById.has(todo.id) ? { ...todo, date: today, order: orderById.get(todo.id) } : todo,
    ),
  );
}

export function purgeOldCompleted(data, today) {
  const todos = data.todos.filter((todo) => !(todo.completed && todo.date < today));
  return todos.length === data.todos.length ? data : withTodos(data, todos);
}

export function updateSettings(data, patch) {
  return { ...data, settings: { ...data.settings, ...patch } };
}
