"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import {
  createComment,
  createPost,
  deleteComment,
  deletePost,
  incrementViews,
  updatePost,
  type MutationOutcome,
} from "@/lib/posts";
import {
  commentSchema,
  errorState,
  passwordOnlySchema,
  postSchema,
  postUpdateSchema,
  toErrorState,
  type FormState,
} from "@/lib/validation";

/**
 * 서버 액션은 UI를 거치지 않고 POST 요청으로도 호출될 수 있으므로
 * 모든 입력을 이 안에서 다시 검증한다.
 */

function text(formData: FormData, key: string): string {
  const value = formData.get(key);
  return typeof value === "string" ? value : "";
}

function outcomeToState(outcome: MutationOutcome): FormState {
  if (outcome === "wrong-password") {
    return errorState("비밀번호가 일치하지 않습니다.", {
      password: ["비밀번호가 일치하지 않습니다."],
    });
  }
  return errorState("글을 찾을 수 없습니다. 이미 삭제되었을 수 있습니다.");
}

/* ---------------- 조회수 ---------------- */

/**
 * 조회수는 상세 페이지 렌더링 중에 올리지 않고, 클라이언트가 한 번 호출한다.
 * 렌더 도중 데이터를 바꾸지 않아도 되고, 새로 고침마다 수치가 부풀지도 않는다.
 */
export async function incrementViewsAction(id: string): Promise<void> {
  if (typeof id !== "string" || !id) return;
  await incrementViews(id);
}

/* ---------------- 글 작성 ---------------- */

export async function createPostAction(
  _prev: FormState,
  formData: FormData,
): Promise<FormState> {
  const raw = {
    category: text(formData, "category"),
    title: text(formData, "title"),
    content: text(formData, "content"),
    author: text(formData, "author"),
    password: text(formData, "password"),
  };

  const parsed = postSchema.safeParse(raw);
  if (!parsed.success) {
    const { password: _omit, ...keep } = raw;
    return toErrorState(parsed.error, keep);
  }

  const id = await createPost(parsed.data);

  revalidatePath("/");
  redirect(`/posts/${id}`);
}

/* ---------------- 글 수정 ---------------- */

export async function updatePostAction(
  _prev: FormState,
  formData: FormData,
): Promise<FormState> {
  const id = text(formData, "id");
  const raw = {
    category: text(formData, "category"),
    title: text(formData, "title"),
    content: text(formData, "content"),
    password: text(formData, "password"),
  };

  if (!id) return errorState("잘못된 요청입니다.");

  const parsed = postUpdateSchema.safeParse(raw);
  if (!parsed.success) {
    const { password: _omit, ...keep } = raw;
    return toErrorState(parsed.error, keep);
  }

  const outcome = await updatePost({ id, ...parsed.data });
  if (outcome !== "ok") {
    const { password: _omit, ...keep } = raw;
    return { ...outcomeToState(outcome), values: keep };
  }

  revalidatePath("/");
  revalidatePath(`/posts/${id}`);
  redirect(`/posts/${id}`);
}

/* ---------------- 글 삭제 ---------------- */

export async function deletePostAction(
  _prev: FormState,
  formData: FormData,
): Promise<FormState> {
  const id = text(formData, "id");
  if (!id) return errorState("잘못된 요청입니다.");

  const parsed = passwordOnlySchema.safeParse({
    password: text(formData, "password"),
  });
  if (!parsed.success) return toErrorState(parsed.error);

  const outcome = await deletePost(id, parsed.data.password);
  if (outcome !== "ok") return outcomeToState(outcome);

  revalidatePath("/");
  redirect("/");
}

/* ---------------- 댓글 작성 ---------------- */

export async function createCommentAction(
  _prev: FormState,
  formData: FormData,
): Promise<FormState> {
  const postId = text(formData, "postId");
  if (!postId) return errorState("잘못된 요청입니다.");

  const raw = {
    author: text(formData, "author"),
    password: text(formData, "password"),
    content: text(formData, "content"),
  };

  const parsed = commentSchema.safeParse(raw);
  if (!parsed.success) {
    const { password: _omit, ...keep } = raw;
    return toErrorState(parsed.error, keep);
  }

  const outcome = await createComment({ postId, ...parsed.data });
  if (outcome !== "ok") return outcomeToState(outcome);

  revalidatePath(`/posts/${postId}`);
  revalidatePath("/");
  return { status: "idle", message: "댓글을 등록했습니다." };
}

/* ---------------- 댓글 삭제 ---------------- */

export async function deleteCommentAction(
  _prev: FormState,
  formData: FormData,
): Promise<FormState> {
  const id = text(formData, "id");
  const postId = text(formData, "postId");
  if (!id || !postId) return errorState("잘못된 요청입니다.");

  const parsed = passwordOnlySchema.safeParse({
    password: text(formData, "password"),
  });
  if (!parsed.success) return toErrorState(parsed.error);

  const outcome = await deleteComment(id, parsed.data.password);
  if (outcome === "wrong-password") {
    return errorState("비밀번호가 일치하지 않습니다.", {
      password: ["비밀번호가 일치하지 않습니다."],
    });
  }
  if (outcome === "not-found") {
    return errorState("댓글을 찾을 수 없습니다.");
  }

  revalidatePath(`/posts/${postId}`);
  revalidatePath("/");
  return { status: "idle", message: "댓글을 삭제했습니다." };
}
