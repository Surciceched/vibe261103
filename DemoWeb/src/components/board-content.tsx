import { InboxIcon, PenLineIcon } from "lucide-react";
import Link from "next/link";

import { BoardPagination } from "@/components/board-pagination";
import { BoardToolbar } from "@/components/board-toolbar";
import { PostList } from "@/components/post-list";
import { Button } from "@/components/ui/button";
import { countByCategory, listPosts } from "@/lib/posts";
import { parseBoardQuery } from "@/lib/query";
import { CATEGORY_VALUES } from "@/lib/types";

/**
 * 목록의 데이터 의존 영역.
 *
 * searchParams를 await하는 지점을 <Suspense> 안쪽으로 내려, URL과 무관한
 * 껍데기(제목·글쓰기 버튼)는 정적 셸로 남고 이 부분만 요청마다 스트리밍된다.
 */
export async function BoardContent({
  searchParams,
}: Pick<PageProps<"/">, "searchParams">) {
  const params = await searchParams;
  const query = parseBoardQuery(params, CATEGORY_VALUES);

  const [result, counts] = await Promise.all([
    listPosts(query),
    countByCategory(),
  ]);

  return (
    <div className="space-y-6">
      <p className="text-sm text-muted-foreground">
        전체 {result.total}건 · {result.page}/{result.totalPages} 페이지
      </p>

      <BoardToolbar query={query} counts={counts} total={result.total} />

      {result.items.length > 0 ? (
        <>
          <PostList posts={result.items} />
          <BoardPagination
            query={query}
            page={result.page}
            totalPages={result.totalPages}
          />
        </>
      ) : (
        <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed py-16 text-center">
          <InboxIcon className="size-8 text-muted-foreground" />
          <div>
            <p className="font-medium">
              {query.q ? "검색 결과가 없습니다." : "아직 글이 없습니다."}
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              {query.q
                ? "다른 검색어로 찾아보세요."
                : "첫 글을 남겨 게시판을 시작해 보세요."}
            </p>
          </div>
          <Button render={<Link href="/posts/new" />} variant="outline">
            <PenLineIcon />
            글쓰기
          </Button>
        </div>
      )}
    </div>
  );
}
