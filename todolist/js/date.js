const pad = (value) => String(value).padStart(2, "0");

// toISOString()은 UTC로 변환되어 한국 시간 오전 9시 이전에 전날이 되므로 현지 시간 값으로 만든다.
export function toDateString(date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

export function todayString() {
  return toDateString(new Date());
}

function parseDate(dateString) {
  const [year, month, day] = dateString.split("-").map(Number);
  return new Date(year, month - 1, day);
}

export function previousDay(dateString) {
  const date = parseDate(dateString);
  date.setDate(date.getDate() - 1);
  return toDateString(date);
}

export function formatDate(dateString) {
  return new Intl.DateTimeFormat("ko-KR", {
    year: "numeric",
    month: "long",
    day: "numeric",
    weekday: "long",
  }).format(parseDate(dateString));
}
