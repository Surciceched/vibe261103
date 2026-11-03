import { MessageSquareIcon } from "lucide-react";

import { CommentForm } from "@/components/comment-form";
import { DeleteCommentDialog } from "@/components/delete-comment-dialog";
import { Separator } from "@/components/ui/separator";
import { formatRelative } from "@/lib/format";
import type { PublicComment } from "@/lib/types";

type Props = {
  postId: string;
  comments: PublicComment[];
};

export function CommentSection({ postId, comments }: Props) {
  return (
    <section aria-labelledby="comments-title" className="space-y-5">
      <h2
        id="comments-title"
        className="flex items-center gap-2 text-lg font-semibold"
      >
        <MessageSquareIcon className="size-4.5 text-muted-foreground" />
        댓글 {comments.length}
      </h2>

      {comments.length > 0 ? (
        <ul className="divide-y rounded-lg border">
          {comments.map((comment) => (
            <li key={comment.id} className="p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="flex items-center gap-2 text-sm">
                    <span className="font-medium">{comment.author}</span>
                    <span className="text-muted-foreground">
                      {formatRelative(comment.createdAt)}
                    </span>
                  </p>
                  <p className="mt-1.5 text-sm whitespace-pre-wrap break-words">
                    {comment.content}
                  </p>
                </div>
                <DeleteCommentDialog
                  commentId={comment.id}
                  postId={postId}
                  author={comment.author}
                />
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <p className="rounded-lg border border-dashed py-8 text-center text-sm text-muted-foreground">
          첫 댓글을 남겨보세요.
        </p>
      )}

      <Separator />
      <CommentForm postId={postId} />
    </section>
  );
}
