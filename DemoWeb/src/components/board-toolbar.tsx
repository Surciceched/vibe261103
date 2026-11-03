import { SearchIcon, XIcon } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { boardHref, SORT_OPTIONS, type BoardQuery } from "@/lib/query";
import { CATEGORIES } from "@/lib/types";
import { cn } from "@/lib/utils";

type Props = {
  query: BoardQuery;
  counts: Record<string, number>;
  total: number;
};

export function BoardToolbar({ query, counts, total }: Props) {
  const allCount = Object.values(counts).reduce((a, b) => a + b, 0);

  return (
    <div className="space-y-4">
      {/* 카테고리 — 링크로 만들어 자바스크립트 없이도 동작한다 */}
      <nav aria-label="분류" className="flex flex-wrap gap-2">
        <CategoryLink
          href={boardHref(query, { category: "", page: 1 })}
          active={!query.category}
          label="전체"
          count={allCount}
        />
        {CATEGORIES.map((c) => (
          <CategoryLink
            key={c.value}
            href={boardHref(query, { category: c.value, page: 1 })}
            active={query.category === c.value}
            label={c.label}
            count={counts[c.value] ?? 0}
          />
        ))}
      </nav>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <form action="/" method="get" className="flex w-full gap-2 sm:max-w-sm">
          {query.category ? (
            <input type="hidden" name="category" value={query.category} />
          ) : null}
          {query.sort !== "latest" ? (
            <input type="hidden" name="sort" value={query.sort} />
          ) : null}

          <div className="relative flex-1">
            <SearchIcon className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              type="search"
              name="q"
              defaultValue={query.q}
              placeholder="제목, 내용, 작성자 검색"
              aria-label="게시글 검색"
              className="pl-8"
            />
          </div>
          <Button type="submit" variant="outline">
            검색
          </Button>
        </form>

        <div className="flex items-center gap-1" role="group" aria-label="정렬">
          {SORT_OPTIONS.map((option) => (
            <Button
              key={option.value}
              render={
                <Link href={boardHref(query, { sort: option.value, page: 1 })} />
              }
              variant={query.sort === option.value ? "secondary" : "ghost"}
              size="sm"
              aria-current={query.sort === option.value ? "true" : undefined}
            >
              {option.label}
            </Button>
          ))}
        </div>
      </div>

      {query.q ? (
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <span>
            <strong className="text-foreground">{query.q}</strong> 검색 결과{" "}
            {total}건
          </span>
          <Button
            render={<Link href={boardHref(query, { q: "", page: 1 })} />}
            variant="ghost"
            size="xs"
          >
            <XIcon />
            검색 해제
          </Button>
        </p>
      ) : null}
    </div>
  );
}

function CategoryLink({
  href,
  active,
  label,
  count,
}: {
  href: string;
  active: boolean;
  label: string;
  count: number;
}) {
  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-sm transition-colors",
        active
          ? "border-primary bg-primary text-primary-foreground"
          : "border-border text-muted-foreground hover:bg-muted hover:text-foreground",
      )}
    >
      {label}
      <span className={cn("text-xs", active ? "opacity-80" : "opacity-60")}>
        {count}
      </span>
    </Link>
  );
}
