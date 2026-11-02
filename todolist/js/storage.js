import { createEmptyData, MAX_TEXT_LENGTH } from "./store.js";

const STORAGE_KEY = "today-todo:v1";
const BACKUP_KEY = "today-todo:backup";
const DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;

function isValidTodo(todo) {
  return (
    todo !== null &&
    typeof todo === "object" &&
    typeof todo.id === "string" &&
    typeof todo.text === "string" &&
    todo.text.length >= 1 &&
    todo.text.length <= MAX_TEXT_LENGTH &&
    typeof todo.completed === "boolean" &&
    typeof todo.date === "string" &&
    DATE_PATTERN.test(todo.date) &&
    Number.isFinite(todo.order) &&
    typeof todo.createdAt === "string" &&
    (todo.completedAt === null || typeof todo.completedAt === "string")
  );
}

function isValidData(data) {
  return (
    data !== null &&
    typeof data === "object" &&
    data.version === 1 &&
    Array.isArray(data.todos) &&
    data.todos.every(isValidTodo) &&
    data.settings !== null &&
    typeof data.settings === "object" &&
    ["system", "light", "dark"].includes(data.settings.theme) &&
    typeof data.settings.completedCollapsed === "boolean"
  );
}

function backUpCorrupted(raw) {
  try {
    localStorage.setItem(BACKUP_KEY, raw);
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    // 백업 공간이 부족해도 앱은 빈 상태로 시작한다.
  }
}

// status: "ok" | "empty" | "corrupted" | "unavailable"
export function load() {
  let raw;
  try {
    raw = localStorage.getItem(STORAGE_KEY);
  } catch {
    return { data: createEmptyData(), status: "unavailable" };
  }
  if (raw === null) return { data: createEmptyData(), status: "empty" };

  try {
    const data = JSON.parse(raw);
    if (isValidData(data)) return { data, status: "ok" };
  } catch {
    // 아래에서 손상된 데이터로 처리한다.
  }
  backUpCorrupted(raw);
  return { data: createEmptyData(), status: "corrupted" };
}

export function save(data) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    return true;
  } catch {
    return false;
  }
}

export function onExternalChange(callback) {
  window.addEventListener("storage", (event) => {
    if (event.key === STORAGE_KEY || event.key === null) callback();
  });
}
