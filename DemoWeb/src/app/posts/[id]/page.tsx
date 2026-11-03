import type { Metadata } from "next";
import { Suspense } from "react";

import { PostDetailSkeleton } from "@/components/board-skeleton";
import { excerpt } from "@/lib/format";
import { getPost } from "@/lib/posts";

import { PostDetail } from "./post-detail";

export async function generateMetadata({
  params,
}: PageProps<"/posts/[id]">): Promise<Metadata> {
  const { id } = await params;
  const post = await getPost(id);
  if (!post) return { title: "글을 찾을 수 없습니다" };

  return {
    title: post.title,
    description: excerpt(post.content, 120),
  };
}

export default function PostDetailPage({ params }: PageProps<"/posts/[id]">) {
  // params를 await하지 않고 넘겨 셸이 URL에 묶이지 않게 한다.
  return (
    <Suspense fallback={<PostDetailSkeleton />}>
      <PostDetail params={params} />
    </Suspense>
  );
}
