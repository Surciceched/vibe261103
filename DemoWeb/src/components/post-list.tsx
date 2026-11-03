import { EyeIcon, MessageSquareIcon } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { excerpt, formatListDate, formatNumber } from "@/lib/format";
import { categoryLabel, type PublicPost } from "@/lib/types";

export function PostList({ posts }: { posts: PublicPost[] }) {
  return (
    <>
      {/* 데스크톱: 표 */}
      <div className="hidden rounded-lg border sm:block">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-20 text-center">분류</TableHead>
              <TableHead>제목</TableHead>
              <TableHead className="w-28">작성자</TableHead>
              <TableHead className="w-20 text-center">작성일</TableHead>
              <TableHead className="w-16 text-right">조회</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {posts.map((post) => (
              <TableRow key={post.id}>
                <TableCell className="text-center">
                  <Badge variant={post.pinned ? "default" : "secondary"}>
                    {post.pinned ? "공지" : categoryLabel(post.category)}
                  </Badge>
                </TableCell>
                <TableCell>
                  <Link
                    href={`/posts/${post.id}`}
                    className="font-medium hover:underline"
                  >
                    {post.title}
                  </Link>
                  {post.commentCount > 0 ? (
                    <span className="ml-2 text-xs text-primary">
                      [{post.commentCount}]
                    </span>
                  ) : null}
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {post.author}
                </TableCell>
                <TableCell className="text-center text-muted-foreground">
                  {formatListDate(post.createdAt)}
                </TableCell>
                <TableCell className="text-right text-muted-foreground">
                  {formatNumber(post.views)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* 모바일: 카드 목록 */}
      <ul className="divide-y rounded-lg border sm:hidden">
        {posts.map((post) => (
          <li key={post.id}>
            <Link href={`/posts/${post.id}`} className="block p-4">
              <div className="mb-1.5 flex items-center gap-2">
                <Badge variant={post.pinned ? "default" : "secondary"}>
                  {post.pinned ? "공지" : categoryLabel(post.category)}
                </Badge>
                <span className="text-xs text-muted-foreground">
                  {post.author} · {formatListDate(post.createdAt)}
                </span>
              </div>
              <p className="font-medium">{post.title}</p>
              <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">
                {excerpt(post.content)}
              </p>
              <div className="mt-2 flex items-center gap-3 text-xs text-muted-foreground">
                <span className="inline-flex items-center gap-1">
                  <EyeIcon className="size-3.5" />
                  {formatNumber(post.views)}
                </span>
                <span className="inline-flex items-center gap-1">
                  <MessageSquareIcon className="size-3.5" />
                  {post.commentCount}
                </span>
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </>
  );
}
