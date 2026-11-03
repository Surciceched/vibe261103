import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";

import { SiteHeader } from "@/components/site-header";
import { ThemeProvider } from "@/components/theme-provider";
import { Toaster } from "@/components/ui/sonner";

import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    default: "DemoWeb 게시판",
    template: "%s · DemoWeb 게시판",
  },
  description:
    "Next.js, TypeScript, shadcn/ui로 만든 웹 게시판입니다. 로그인 없이 글을 쓰고 비밀번호로 수정·삭제할 수 있습니다.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="ko"
      suppressHydrationWarning
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col">
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <SiteHeader />
          <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8">
            {children}
          </main>
          <footer className="border-t py-6">
            <div className="mx-auto w-full max-w-5xl px-4 text-sm text-muted-foreground">
              DemoWeb · Next.js 16 · TypeScript · shadcn/ui
            </div>
          </footer>
          <Toaster position="top-center" />
        </ThemeProvider>
      </body>
    </html>
  );
}
