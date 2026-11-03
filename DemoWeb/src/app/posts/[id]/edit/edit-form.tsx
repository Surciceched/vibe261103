import { notFound } from "next/navigation";

import { PostForm } from "@/components/post-form";
import { updatePostAction } from "@/lib/actions";
import { getPost } from "@/lib/posts";

/** 수정 화면의 데이터 의존 영역. params를 이 안에서 await한다. */
export async function EditForm({
  params,
}: Pick<PageProps<"/posts/[id]/edit">, "params">) {
  const { id } = await params;

  const post = await getPost(id);
  if (!post) notFound();

  return (
    <>
      <p className="text-sm text-muted-foreground">
        작성자 <strong className="text-foreground">{post.author}</strong> ·
        수정하려면 글을 쓸 때 입력한 비밀번호가 필요합니다.
      </p>

      <PostForm
        action={updatePostAction}
        mode="edit"
        postId={post.id}
        defaults={{
          category: post.category,
          title: post.title,
          content: post.content,
        }}
        cancelHref={`/posts/${post.id}`}
      />
    </>
  );
}
