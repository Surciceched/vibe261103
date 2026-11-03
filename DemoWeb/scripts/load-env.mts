/** 스크립트 실행 시 .env.local → .env 순서로 환경 변수를 읽어온다. */
export function loadEnv(): void {
  if (process.env.DATABASE_URL) return;

  for (const file of [".env.local", ".env"]) {
    try {
      process.loadEnvFile(file);
      if (process.env.DATABASE_URL) return;
    } catch {
      // 파일이 없으면 다음 후보로 넘어간다.
    }
  }
}
