import type { Metadata } from "next";

import { PostForm } from "@/components/post-form";
import { createPostAction } from "@/lib/actions";

export const metadata: Metadata = {
  title: "글쓰기",
};

export default function NewPostPage() {
  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">글쓰기</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          로그인 없이 글을 쓸 수 있습니다. 입력한 비밀번호로 나중에 수정·삭제할
          수 있습니다.
        </p>
      </div>

      <PostForm action={createPostAction} mode="create" cancelHref="/" />
    </div>
  );
}
