import { Skeleton } from "@/components/ui/skeleton";

/** 목록 영역이 스트리밍되기 전 자리를 잡아 두는 뼈대 */
export function BoardSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-5 w-40" />

      <div className="flex flex-wrap gap-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-8 w-20 rounded-full" />
        ))}
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:justify-between">
        <Skeleton className="h-9 w-full sm:max-w-sm" />
        <Skeleton className="h-9 w-48" />
      </div>

      <div className="space-y-px rounded-lg border p-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-10 w-full" />
        ))}
      </div>
    </div>
  );
}

/** 상세 화면용 뼈대 */
export function PostDetailSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-6 w-16 rounded-full" />
      <Skeleton className="h-8 w-3/4" />
      <Skeleton className="h-4 w-56" />
      <div className="space-y-2 pt-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-4 w-full" />
        ))}
        <Skeleton className="h-4 w-2/3" />
      </div>
      <div className="flex gap-2 pt-2">
        <Skeleton className="h-8 w-20" />
        <Skeleton className="h-8 w-20" />
      </div>
    </div>
  );
}

/** 작성·수정 폼용 뼈대 */
export function PostFormSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex gap-2">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-8 w-20 rounded-full" />
        ))}
      </div>
      <Skeleton className="h-9 w-full" />
      <Skeleton className="h-64 w-full" />
      <div className="grid gap-4 sm:grid-cols-2">
        <Skeleton className="h-9 w-full" />
        <Skeleton className="h-9 w-full" />
      </div>
      <Skeleton className="h-9 w-32" />
    </div>
  );
}
