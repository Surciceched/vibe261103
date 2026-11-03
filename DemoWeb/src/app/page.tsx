import { PenLineIcon } from "lucide-react";
import Link from "next/link";
import { Suspense } from "react";

import { BoardContent } from "@/components/board-content";
import { BoardSkeleton } from "@/components/board-skeleton";
import { Button } from "@/components/ui/button";

export default function BoardPage({ searchParams }: PageProps<"/">) {
  // searchParams를 여기서 await하지 않는다. 프로미스를 그대로 자식에게 넘겨
  // 이 껍데기는 정적 셸로 남고 목록만 요청마다 스트리밍된다.
  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between gap-4">
        <h1 className="text-2xl font-semibold tracking-tight">게시판</h1>
        <Button render={<Link href="/posts/new" />} className="hidden sm:flex">
          <PenLineIcon />
          글쓰기
        </Button>
      </div>

      <Suspense fallback={<BoardSkeleton />}>
        <BoardContent searchParams={searchParams} />
      </Suspense>
    </div>
  );
}
