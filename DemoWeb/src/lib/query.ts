import type { SortOrder } from "@/lib/types";

export type BoardQuery = {
  q: string;
  category: string;
  sort: SortOrder;
  page: number;
};

const SORTS: SortOrder[] = ["latest", "views", "comments"];

export const SORT_OPTIONS: { value: SortOrder; label: string }[] = [
  { value: "latest", label: "최신순" },
  { value: "views", label: "조회순" },
  { value: "comments", label: "댓글순" },
];

type RawSearchParams = Record<string, string | string[] | undefined>;

function one(value: string | string[] | undefined): string {
  if (Array.isArray(value)) return value[0] ?? "";
  return value ?? "";
}

/** URL 쿼리를 안전한 값으로 정규화한다. */
export function parseBoardQuery(
  params: RawSearchParams,
  validCategories: readonly string[],
): BoardQuery {
  const rawCategory = one(params.category);
  const rawSort = one(params.sort) as SortOrder;
  const pageNumber = Number.parseInt(one(params.page), 10);

  return {
    q: one(params.q).slice(0, 100),
    category: validCategories.includes(rawCategory) ? rawCategory : "",
    sort: SORTS.includes(rawSort) ? rawSort : "latest",
    page: Number.isFinite(pageNumber) && pageNumber > 0 ? pageNumber : 1,
  };
}

/** 현재 조건을 유지하면서 일부만 바꾼 링크를 만든다. */
export function boardHref(
  query: BoardQuery,
  overrides: Partial<BoardQuery> = {},
): string {
  const merged = { ...query, ...overrides };
  const search = new URLSearchParams();

  if (merged.q) search.set("q", merged.q);
  if (merged.category) search.set("category", merged.category);
  if (merged.sort !== "latest") search.set("sort", merged.sort);
  if (merged.page > 1) search.set("page", String(merged.page));

  const qs = search.toString();
  return qs ? `/?${qs}` : "/";
}
