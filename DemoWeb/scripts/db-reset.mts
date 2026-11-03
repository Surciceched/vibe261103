/**
 * 테이블을 지우고 다시 만든 뒤 예시 데이터를 넣는다.
 * 게시판 데이터가 모두 사라진다.
 *
 *   npm run db:reset
 */
import { loadEnv } from "./load-env.mts";

loadEnv();

const { applySchema, dropSchema, seedDatabase, countPosts } = await import(
  "../src/lib/db-admin.ts"
);

await dropSchema();
console.log("기존 테이블을 삭제했습니다.");

await applySchema();
console.log("스키마를 다시 적용했습니다.");

await seedDatabase();
console.log(`예시 데이터를 넣었습니다. 현재 글 수: ${await countPosts()}건`);
