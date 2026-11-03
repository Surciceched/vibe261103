"use client";

import { AlertCircleIcon, Loader2Icon } from "lucide-react";
import Link from "next/link";
import { useActionState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { IDLE_STATE, type FormState } from "@/lib/validation";
import { CATEGORIES, type CategoryValue } from "@/lib/types";
import { cn } from "@/lib/utils";

type Action = (state: FormState, formData: FormData) => Promise<FormState>;

type Props = {
  action: Action;
  mode: "create" | "edit";
  postId?: string;
  defaults?: {
    category?: CategoryValue;
    title?: string;
    content?: string;
    author?: string;
  };
  cancelHref: string;
};

export function PostForm({
  action,
  mode,
  postId,
  defaults,
  cancelHref,
}: Props) {
  const [state, formAction, isPending] = useActionState(action, IDLE_STATE);

  // 검증 실패 후에는 서버가 돌려준 값을 우선 보여준다.
  const value = (key: string, fallback?: string) =>
    state.values?.[key] ?? fallback ?? "";
  const errors = state.fieldErrors ?? {};
  const selectedCategory =
    (value("category", defaults?.category) as CategoryValue) || "free";

  return (
    <form action={formAction} className="space-y-6">
      {postId ? <input type="hidden" name="id" value={postId} /> : null}

      {state.status === "error" && state.message ? (
        <p
          role="alert"
          className="flex items-center gap-2 rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"
        >
          <AlertCircleIcon className="size-4 shrink-0" />
          {state.message}
        </p>
      ) : null}

      <fieldset className="space-y-2">
        <legend className="text-sm font-medium">분류</legend>
        <div className="flex flex-wrap gap-2">
          {CATEGORIES.filter((c) => c.value !== "notice").map((c) => (
            <label
              key={c.value}
              className={cn(
                "cursor-pointer rounded-full border px-3.5 py-1.5 text-sm transition-colors",
                "has-checked:border-primary has-checked:bg-primary has-checked:text-primary-foreground",
                "has-focus-visible:ring-3 has-focus-visible:ring-ring/50",
                "hover:bg-muted has-checked:hover:bg-primary",
              )}
            >
              <input
                type="radio"
                name="category"
                value={c.value}
                defaultChecked={selectedCategory === c.value}
                className="sr-only"
              />
              {c.label}
            </label>
          ))}
        </div>
        <FieldError messages={errors.category} />
      </fieldset>

      <div className="space-y-2">
        <Label htmlFor="title">제목</Label>
        <Input
          id="title"
          name="title"
          defaultValue={value("title", defaults?.title)}
          placeholder="제목을 입력하세요"
          maxLength={100}
          required
          aria-invalid={errors.title ? true : undefined}
        />
        <FieldError messages={errors.title} />
      </div>

      <div className="space-y-2">
        <Label htmlFor="content">내용</Label>
        <Textarea
          id="content"
          name="content"
          defaultValue={value("content", defaults?.content)}
          placeholder="내용을 입력하세요"
          rows={12}
          maxLength={5000}
          required
          aria-invalid={errors.content ? true : undefined}
        />
        <FieldError messages={errors.content} />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {mode === "create" ? (
          <div className="space-y-2">
            <Label htmlFor="author">작성자</Label>
            <Input
              id="author"
              name="author"
              defaultValue={value("author", defaults?.author)}
              placeholder="이름"
              maxLength={20}
              required
              aria-invalid={errors.author ? true : undefined}
            />
            <FieldError messages={errors.author} />
          </div>
        ) : null}

        <div className="space-y-2">
          <Label htmlFor="password">비밀번호</Label>
          <Input
            id="password"
            name="password"
            type="password"
            placeholder="4자 이상"
            autoComplete={mode === "create" ? "new-password" : "current-password"}
            minLength={4}
            required
            aria-invalid={errors.password ? true : undefined}
          />
          <FieldError messages={errors.password} />
          <p className="text-xs text-muted-foreground">
            {mode === "create"
              ? "수정·삭제할 때 필요합니다. 잊지 마세요."
              : "글을 쓸 때 입력한 비밀번호를 입력하세요."}
          </p>
        </div>
      </div>

      <div className="flex gap-2">
        <Button type="submit" disabled={isPending}>
          {isPending ? <Loader2Icon className="animate-spin" /> : null}
          {mode === "create" ? "등록" : "수정 완료"}
        </Button>
        <Button
          render={<Link href={cancelHref} />}
          variant="outline"
          type="button"
        >
          취소
        </Button>
      </div>
    </form>
  );
}

function FieldError({ messages }: { messages?: string[] }) {
  if (!messages?.length) return null;
  return (
    <p className="text-sm text-destructive" role="alert">
      {messages[0]}
    </p>
  );
}
