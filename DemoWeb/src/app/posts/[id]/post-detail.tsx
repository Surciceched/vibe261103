import {
  ChevronLeftIcon,
  ChevronRightIcon,
  EyeIcon,
  ListIcon,
  PencilIcon,
} from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { CommentSection } from "@/components/comment-section";
import { DeletePostDialog } from "@/components/delete-post-dialog";
import { ViewTracker } from "@/components/view-tracker";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { formatDateTime, formatNumber } from "@/lib/format";
import { getNeighbors, getPost, listComments } from "@/lib/posts";
import { categoryLabel } from "@/lib/types";

/**
 * 상세 화면의 데이터 의존 영역. params를 이 안에서 await한다.
 */
export async function PostDetail({
  params,
}: Pick<PageProps<"/posts/[id]">, "params">) {
  const { id } = await params;

  const post = await getPost(id);
  if (!post) notFound();

  const [comments, neighbors] = await Promise.all([
    listComments(id),
    getNeighbors(id),
  ]);

  const edited = post.updatedAt !== post.createdAt;

  return (
    <article className="space-y-6">
      <ViewTracker postId={post.id} />

      <header className="space-y-3">
        <div className="flex items-center gap-2">
          <Badge variant={post.pinned ? "default" : "secondary"}>
            {post.pinned ? "공지" : categoryLabel(post.category)}
          </Badge>
          <Button
            render={<Link href="/" />}
            variant="ghost"
            size="xs"
            className="ml-auto"
          >
            <ListIcon />
            목록
          </Button>
        </div>

        <h1 className="text-2xl font-semibold tracking-tight break-words">
          {post.title}
        </h1>

        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground">
          <span className="font-medium text-foreground">{post.author}</span>
          <span>{formatDateTime(post.createdAt)}</span>
          {edited ? <span>· 수정 {formatDateTime(post.updatedAt)}</span> : null}
          <span className="inline-flex items-center gap-1">
            <EyeIcon className="size-3.5" />
            {formatNumber(post.views)}
          </span>
        </div>
      </header>

      <Separator />

      <div className="min-h-32 text-[0.9375rem] leading-7 whitespace-pre-wrap break-words">
        {post.content}
      </div>

      <div className="flex gap-2">
        <Button
          render={<Link href={`/posts/${post.id}/edit`} />}
          variant="outline"
          size="sm"
        >
          <PencilIcon />
          수정
        </Button>
        <DeletePostDialog postId={post.id} />
      </div>

      <Separator />

      {/* 이전 / 다음 글 */}
      {neighbors.prev || neighbors.next ? (
        <nav aria-label="글 이동" className="divide-y rounded-lg border text-sm">
          {neighbors.next ? (
            <Link
              href={`/posts/${neighbors.next.id}`}
              className="flex items-center gap-2 p-3 hover:bg-muted"
            >
              <ChevronLeftIcon className="size-4 shrink-0 text-muted-foreground" />
              <span className="shrink-0 text-muted-foreground">다음 글</span>
              <span className="truncate">{neighbors.next.title}</span>
            </Link>
          ) : null}
          {neighbors.prev ? (
            <Link
              href={`/posts/${neighbors.prev.id}`}
              className="flex items-center gap-2 p-3 hover:bg-muted"
            >
              <ChevronRightIcon className="size-4 shrink-0 text-muted-foreground" />
              <span className="shrink-0 text-muted-foreground">이전 글</span>
              <span className="truncate">{neighbors.prev.title}</span>
            </Link>
          ) : null}
        </nav>
      ) : null}

      <CommentSection postId={post.id} comments={comments} />
    </article>
  );
}
