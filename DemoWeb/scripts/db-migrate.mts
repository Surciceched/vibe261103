/**
 * Neon에 테이블과 인덱스를 만든다. 여러 번 실행해도 안전하다.
 *
 *   npm run db:migrate
 */
import { loadEnv } from "./load-env.mts";

loadEnv();

const { applySchema } = await import("../src/lib/db-admin.ts");

const count = await applySchema();
console.log(`스키마를 적용했습니다. 실행한 문장: ${count}개`);
