import { FileQuestionIcon } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center gap-4 py-20 text-center">
      <FileQuestionIcon className="size-10 text-muted-foreground" />
      <div>
        <h1 className="text-xl font-semibold">페이지를 찾을 수 없습니다</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          주소가 바뀌었거나 글이 삭제되었을 수 있습니다.
        </p>
      </div>
      <Button render={<Link href="/" />}>목록으로</Button>
    </div>
  );
}
