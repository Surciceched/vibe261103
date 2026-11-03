"use client";

import { Loader2Icon, Trash2Icon } from "lucide-react";
import { useActionState } from "react";

import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { deletePostAction } from "@/lib/actions";
import { IDLE_STATE } from "@/lib/validation";

export function DeletePostDialog({ postId }: { postId: string }) {
  const [state, formAction, isPending] = useActionState(
    deletePostAction,
    IDLE_STATE,
  );
  const error = state.fieldErrors?.password?.[0] ?? state.message;

  return (
    <AlertDialog>
      <AlertDialogTrigger
        render={
          <Button variant="destructive" size="sm">
            <Trash2Icon />
            삭제
          </Button>
        }
      />
      <AlertDialogContent>
        <form action={formAction}>
          <input type="hidden" name="id" value={postId} />

          <AlertDialogHeader>
            <AlertDialogTitle>글을 삭제할까요?</AlertDialogTitle>
            <AlertDialogDescription>
              글에 달린 댓글도 함께 삭제됩니다. 되돌릴 수 없습니다.
            </AlertDialogDescription>
          </AlertDialogHeader>

          <div className="my-4 space-y-2">
            <Label htmlFor="delete-password">비밀번호</Label>
            <Input
              id="delete-password"
              name="password"
              type="password"
              autoComplete="current-password"
              placeholder="글 작성 시 입력한 비밀번호"
              required
              aria-invalid={state.status === "error" ? true : undefined}
            />
            {state.status === "error" && error ? (
              <p className="text-sm text-destructive" role="alert">
                {error}
              </p>
            ) : null}
          </div>

          <AlertDialogFooter>
            <AlertDialogCancel type="button">취소</AlertDialogCancel>
            <Button type="submit" variant="destructive" disabled={isPending}>
              {isPending ? <Loader2Icon className="animate-spin" /> : null}
              삭제
            </Button>
          </AlertDialogFooter>
        </form>
      </AlertDialogContent>
    </AlertDialog>
  );
}
