"use client";

import { MoonIcon, SunIcon } from "lucide-react";
import { useTheme } from "next-themes";

import { Button } from "@/components/ui/button";

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();

  return (
    <Button
      variant="ghost"
      size="icon"
      aria-label="밝은 테마와 어두운 테마 전환"
      onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
    >
      {/*
        서버와 클라이언트의 첫 렌더가 어긋나지 않도록 두 아이콘을 모두 그리고
        표시 여부는 CSS(.dark 클래스)에 맡긴다. 상태도, 마운트 플래그도 필요 없다.
      */}
      <SunIcon className="hidden dark:block" />
      <MoonIcon className="dark:hidden" />
    </Button>
  );
}
