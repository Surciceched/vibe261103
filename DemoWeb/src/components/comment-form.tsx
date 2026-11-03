"use client";

import { Loader2Icon, SendIcon } from "lucide-react";
import { useActionState, useEffect, useRef } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { createCommentAction } from "@/lib/actions";
import { IDLE_STATE } from "@/lib/validation";

export function CommentForm({ postId }: { postId: string }) {
  const [state, formAction, isPending] = useActionState(
    createCommentAction,
    IDLE_STATE,
  );
  const formRef = useRef<HTMLFormElement>(null);
  const errors = state.fieldErrors ?? {};

  useEffect(() => {
    if (state.status === "idle" && state.message) {
      toast.success(state.message);
      formRef.current?.reset();
    }
  }, [state]);

  return (
    <form ref={formRef} action={formAction} className="space-y-3">
      <input type="hidden" name="postId" value={postId} />

      <div className="grid gap-3 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="comment-author">작성자</Label>
          <Input
            id="comment-author"
            name="author"
            defaultValue={state.values?.author ?? ""}
            placeholder="이름"
            maxLength={20}
            required
            aria-invalid={errors.author ? true : undefined}
          />
          {errors.author ? (
            <p className="text-sm text-destructive" role="alert">
              {errors.author[0]}
            </p>
          ) : null}
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="comment-password">비밀번호</Label>
          <Input
            id="comment-password"
            name="password"
            type="password"
            autoComplete="new-password"
            placeholder="4자 이상 · 삭제할 때 필요"
            minLength={4}
            required
            aria-invalid={errors.password ? true : undefined}
          />
          {errors.password ? (
            <p className="text-sm text-destructive" role="alert">
              {errors.password[0]}
            </p>
          ) : null}
        </div>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="comment-content">댓글</Label>
        <Textarea
          id="comment-content"
          name="content"
          defaultValue={state.values?.content ?? ""}
          placeholder="댓글을 입력하세요"
          rows={3}
          maxLength={500}
          required
          aria-invalid={errors.content ? true : undefined}
        />
        {errors.content ? (
          <p className="text-sm text-destructive" role="alert">
            {errors.content[0]}
          </p>
        ) : null}
      </div>

      <div className="flex items-center gap-3">
        <Button type="submit" disabled={isPending}>
          {isPending ? (
            <Loader2Icon className="animate-spin" />
          ) : (
            <SendIcon />
          )}
          댓글 등록
        </Button>
        {state.status === "error" && state.message ? (
          <p className="text-sm text-destructive" role="alert">
            {state.message}
          </p>
        ) : null}
      </div>
    </form>
  );
}
