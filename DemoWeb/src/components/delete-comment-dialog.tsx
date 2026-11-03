"use client";

import { Loader2Icon, XIcon } from "lucide-react";
import { useState, useTransition, type FormEvent } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { deleteCommentAction } from "@/lib/actions";
import { IDLE_STATE } from "@/lib/validation";

type Props = {
  commentId: string;
  postId: string;
  author: string;
};

export function DeleteCommentDialog({ commentId, postId, author }: Props) {
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const inputId = `comment-delete-${commentId}`;

  /**
   * 성공하면 대화상자를 닫아야 하므로 폼 action 대신 직접 호출한다.
   * 효과(useEffect) 안에서 상태를 바꾸지 않기 위한 선택이다.
   */
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    setError(null);

    startTransition(async () => {
      const result = await deleteCommentAction(IDLE_STATE, formData);

      if (result.status === "error") {
        setError(result.fieldErrors?.password?.[0] ?? result.message ?? null);
        return;
      }

      toast.success(result.message ?? "댓글을 삭제했습니다.");
      setOpen(false);
    });
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (!next) setError(null);
      }}
    >
      <DialogTrigger
        render={
          <Button
            variant="ghost"
            size="icon-xs"
            aria-label={`${author}님의 댓글 삭제`}
          >
            <XIcon />
          </Button>
        }
      />
      <DialogContent>
        <form onSubmit={handleSubmit}>
          <input type="hidden" name="id" value={commentId} />
          <input type="hidden" name="postId" value={postId} />

          <DialogHeader>
            <DialogTitle>댓글을 삭제할까요?</DialogTitle>
            <DialogDescription>
              댓글을 쓸 때 입력한 비밀번호를 입력하세요.
            </DialogDescription>
          </DialogHeader>

          <div className="my-4 space-y-2">
            <Label htmlFor={inputId}>비밀번호</Label>
            <Input
              id={inputId}
              name="password"
              type="password"
              autoComplete="current-password"
              required
              aria-invalid={error ? true : undefined}
            />
            {error ? (
              <p className="text-sm text-destructive" role="alert">
                {error}
              </p>
            ) : null}
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setOpen(false)}
            >
              취소
            </Button>
            <Button type="submit" variant="destructive" disabled={isPending}>
              {isPending ? <Loader2Icon className="animate-spin" /> : null}
              삭제
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
