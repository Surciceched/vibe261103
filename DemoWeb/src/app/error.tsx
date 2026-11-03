"use client";

import { RotateCcwIcon, TriangleAlertIcon } from "lucide-react";
import { useEffect } from "react";

import { Button } from "@/components/ui/button";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex flex-col items-center gap-4 py-20 text-center">
      <TriangleAlertIcon className="size-10 text-destructive" />
      <div>
        <h1 className="text-xl font-semibold">문제가 발생했습니다</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          잠시 후 다시 시도해 주세요.
        </p>
      </div>
      <Button onClick={reset} variant="outline">
        <RotateCcwIcon />
        다시 시도
      </Button>
    </div>
  );
}
