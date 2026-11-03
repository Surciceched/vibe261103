import type { Metadata } from "next";
import { Suspense } from "react";

import { PostFormSkeleton } from "@/components/board-skeleton";

import { EditForm } from "./edit-form";

export const metadata: Metadata = {
  title: "글 수정",
};

export default function EditPostPage({
  params,
}: PageProps<"/posts/[id]/edit">) {
  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <h1 className="text-2xl font-semibold tracking-tight">글 수정</h1>

      <Suspense fallback={<PostFormSkeleton />}>
        <EditForm params={params} />
      </Suspense>
    </div>
  );
}
