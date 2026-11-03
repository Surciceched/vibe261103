/**
 * 예시 글·댓글을 넣는다. 이미 같은 id가 있으면 건너뛴다.
 *
 *   npm run db:seed
 */
import { loadEnv } from "./load-env.mts";

loadEnv();

const { seedDatabase, countPosts } = await import("../src/lib/db-admin.ts");

const result = await seedDatabase();
console.log(
  `예시 데이터를 넣었습니다 (글 ${result.posts}건, 댓글 ${result.comments}건 기준).`,
);
console.log(`현재 글 수: ${await countPosts()}건`);
console.log("예시 글과 댓글의 비밀번호는 모두 1234입니다.");
