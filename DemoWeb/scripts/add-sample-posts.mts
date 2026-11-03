/**
 * 페이지네이션 등 목록 UI를 확인할 때 쓰는 더미 글 생성 스크립트.
 *
 *   npx tsx scripts/add-sample-posts.mts 8
 */
import { createPost } from "../src/lib/posts.ts";

const count = Number.parseInt(process.argv[2] ?? "8", 10) || 8;

for (let i = 1; i <= count; i += 1) {
  await createPost({
    category: "free",
    title: `목록 확인용 더미 글 ${i}`,
    content: `페이지네이션과 목록 레이아웃을 확인하기 위한 더미 본문입니다. (${i})`,
    author: "테스터",
    password: "pw1234",
  });
}

console.log(`${count}건을 추가했습니다. 되돌리려면 npm run seed:reset`);
