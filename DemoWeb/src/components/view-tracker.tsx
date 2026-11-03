"use client";

import { useEffect, useRef } from "react";

import { incrementViewsAction } from "@/lib/actions";

/**
 * 같은 세션에서 같은 글을 여러 번 열어도 조회수는 한 번만 올린다.
 * 화면에 아무것도 그리지 않는다.
 */
export function ViewTracker({ postId }: { postId: string }) {
  const fired = useRef(false);

  useEffect(() => {
    if (fired.current) return;
    fired.current = true;

    const key = `viewed:${postId}`;
    try {
      if (sessionStorage.getItem(key)) return;
      sessionStorage.setItem(key, "1");
    } catch {
      // 스토리지를 쓸 수 없으면 그대로 집계한다.
    }

    void incrementViewsAction(postId);
  }, [postId]);

  return null;
}
