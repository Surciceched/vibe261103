/**
 * 데이터 계층 스모크 테스트 (Neon / PostgreSQL).
 *
 *   npm run smoke
 *
 * .env.local의 DATABASE_URL을 그대로 쓴다. 테스트가 만드는 글은 제목에
 * 고유 표식을 넣어 그 표식으로만 조회하고, 끝나면 표식이 붙은 행을 모두 지운다.
 * 기존 데이터는 읽기만 하고 바꾸지 않는다. (댓글은 ON DELETE CASCADE로 함께 삭제)
 */
import assert from "node:assert/strict";
import { randomUUID } from "node:crypto";

import { loadEnv } from "./load-env.mts";

loadEnv();

const { query } = await import("../src/lib/db.ts");
const { applySchema } = await import("../src/lib/db-admin.ts");
const {
  checkPostPassword,
  countByCategory,
  createComment,
  createPost,
  deleteComment,
  deletePost,
  getNeighbors,
  getPost,
  incrementViews,
  listComments,
  listPosts,
  updatePost,
} = await import("../src/lib/posts.ts");

/** 이번 실행에서만 쓰는 표식. 제목·본문에 넣어 테스트 행만 골라낸다. */
const MARK = `smoke${randomUUID().slice(0, 8)}`;

let passed = 0;
async function check(name: string, run: () => Promise<void> | void) {
  await run();
  passed += 1;
  console.log(`  ok  ${name}`);
}

async function cleanup(): Promise<number> {
  const rows = await query<{ id: string }>(
    `DELETE FROM posts WHERE title LIKE '%' || $1 || '%' RETURNING id`,
    [MARK],
  );
  return rows.length;
}

try {
  await applySchema();
  console.log(`표식: ${MARK}\n`);

  /* ---- 기존(예시) 데이터 읽기 ---- */
  await check("예시 데이터를 읽어온다", async () => {
    const result = await listPosts();
    assert.ok(result.total >= 7, `글이 7건 이상이어야 함 (현재 ${result.total})`);
  });

  await check("공지가 목록 맨 위에 온다", async () => {
    const { items } = await listPosts();
    assert.equal(items[0].pinned, true);
    assert.equal(items[0].category, "notice");
  });

  await check("공개 데이터에 비밀번호 해시가 없다", async () => {
    const { items } = await listPosts();
    assert.ok(!("passwordHash" in items[0]));
    const comments = await listComments("p-dev-next16");
    assert.ok(comments.length > 0);
    assert.ok(!("passwordHash" in comments[0]));
  });

  await check("카테고리로 거를 수 있다", async () => {
    const { items } = await listPosts({ category: "dev" });
    assert.ok(items.length > 0);
    assert.ok(items.every((p) => p.category === "dev"));
  });

  await check("제목·내용·작성자로 검색된다", async () => {
    assert.ok((await listPosts({ q: "shadcn" })).total >= 1);
    assert.ok((await listPosts({ q: "제네릭" })).total >= 1);
    assert.ok((await listPosts({ q: "민수" })).total >= 1);
    assert.equal((await listPosts({ q: "없는단어xyz123" })).total, 0);
  });

  await check("검색은 대소문자를 가리지 않는다", async () => {
    const lower = await listPosts({ q: "shadcn" });
    const upper = await listPosts({ q: "SHADCN" });
    assert.equal(lower.total, upper.total);
    assert.ok(upper.total >= 1);
  });

  await check("댓글 수가 집계된다", async () => {
    const post = await getPost("p-dev-next16");
    assert.equal(post?.commentCount, 2);
  });

  await check("없는 글은 null을 돌려준다", async () => {
    assert.equal(await getPost("p-does-not-exist"), null);
  });

  await check("카테고리별 개수를 센다", async () => {
    const counts = await countByCategory();
    assert.ok((counts.dev ?? 0) >= 2);
    assert.ok((counts.notice ?? 0) >= 1);
  });

  await check("이전·다음 글을 찾는다", async () => {
    const { prev, next } = await getNeighbors("p-qna-ts-generic");
    assert.ok(prev, "이전 글이 있어야 함");
    assert.ok(next, "다음 글이 있어야 함");
    assert.notEqual(prev.id, next.id);
  });

  await check("정렬 기준이 단조성을 지킨다", async () => {
    // 공지는 정렬보다 우선해 맨 위에 고정되므로 제외하고 본다.
    const byViews = await listPosts({ sort: "views", perPage: 50 });
    const views = byViews.items.filter((p) => !p.pinned).map((p) => p.views);
    assert.deepEqual(views, [...views].sort((a, b) => b - a));

    const byComments = await listPosts({ sort: "comments", perPage: 50 });
    const counts = byComments.items
      .filter((p) => !p.pinned)
      .map((p) => p.commentCount);
    assert.deepEqual(counts, [...counts].sort((a, b) => b - a));
  });

  await check("검색 중에는 공지를 고정하지 않는다", async () => {
    // "게시판"은 공지(가장 오래된 글)와 다른 글에 모두 들어 있다.
    const { items } = await listPosts({ q: "게시판" });
    assert.ok(items.length >= 2);
    assert.ok(items.some((p) => p.pinned));
    assert.equal(items[0].pinned, false);
  });

  /* ---- 작성 ---- */
  let newId = "";
  await check("글을 작성한다", async () => {
    const before = (await listPosts()).total;

    newId = await createPost({
      category: "free",
      title: `${MARK} 작성 확인`,
      content: `본문 ${MARK}`,
      author: "테스터",
      password: "pw1234",
    });

    const post = await getPost(newId);
    assert.equal(post?.title, `${MARK} 작성 확인`);
    assert.equal(post?.views, 0);
    assert.equal(post?.pinned, false);
    assert.equal((await listPosts()).total, before + 1);
  });

  await check("표식으로 검색하면 테스트 글만 나온다", async () => {
    const { total, items } = await listPosts({ q: MARK });
    assert.equal(total, 1);
    assert.equal(items[0].id, newId);
  });

  await check("조회수가 올라간다", async () => {
    await incrementViews(newId);
    await incrementViews(newId);
    assert.equal((await getPost(newId))?.views, 2);
  });

  /* ---- 비밀번호 ---- */
  await check("맞는 비밀번호를 통과시킨다", async () => {
    assert.equal(await checkPostPassword(newId, "pw1234"), "ok");
  });

  await check("틀린 비밀번호를 막는다", async () => {
    assert.equal(await checkPostPassword(newId, "wrong"), "wrong-password");
  });

  await check("없는 글의 비밀번호 확인은 not-found", async () => {
    assert.equal(await checkPostPassword("p-nope", "pw1234"), "not-found");
  });

  /* ---- 수정 ---- */
  await check("틀린 비밀번호로는 수정되지 않는다", async () => {
    const outcome = await updatePost({
      id: newId,
      category: "dev",
      title: `${MARK} 바뀌면 안 됨`,
      content: "바뀌면 안 됨",
      password: "wrong",
    });
    assert.equal(outcome, "wrong-password");
    assert.equal((await getPost(newId))?.title, `${MARK} 작성 확인`);
  });

  await check("맞는 비밀번호로 수정된다", async () => {
    const outcome = await updatePost({
      id: newId,
      category: "dev",
      title: `${MARK} 수정됨`,
      content: `수정된 내용 ${MARK}`,
      password: "pw1234",
    });
    assert.equal(outcome, "ok");

    const post = await getPost(newId);
    assert.equal(post?.title, `${MARK} 수정됨`);
    assert.equal(post?.category, "dev");
    assert.notEqual(post?.updatedAt, post?.createdAt);
  });

  await check("없는 글 수정은 not-found", async () => {
    const outcome = await updatePost({
      id: "p-nope",
      category: "dev",
      title: "아무거나",
      content: "아무거나",
      password: "pw1234",
    });
    assert.equal(outcome, "not-found");
  });

  /* ---- 댓글 ---- */
  await check("댓글을 작성한다", async () => {
    assert.equal(
      await createComment({
        postId: newId,
        author: "댓글러",
        password: "cm1234",
        content: "첫 댓글입니다.",
      }),
      "ok",
    );
    assert.equal((await listComments(newId)).length, 1);
    assert.equal((await getPost(newId))?.commentCount, 1);
  });

  await check("없는 글에는 댓글을 달 수 없다", async () => {
    assert.equal(
      await createComment({
        postId: "p-nope",
        author: "댓글러",
        password: "cm1234",
        content: "달리면 안 됨",
      }),
      "not-found",
    );
  });

  await check("틀린 비밀번호로는 댓글이 삭제되지 않는다", async () => {
    const [comment] = await listComments(newId);
    assert.equal(await deleteComment(comment.id, "wrong"), "wrong-password");
    assert.equal((await listComments(newId)).length, 1);
  });

  await check("맞는 비밀번호로 댓글이 삭제된다", async () => {
    const [comment] = await listComments(newId);
    assert.equal(await deleteComment(comment.id, "cm1234"), "ok");
    assert.equal((await listComments(newId)).length, 0);
  });

  /* ---- 삭제 ---- */
  await check("틀린 비밀번호로는 글이 삭제되지 않는다", async () => {
    assert.equal(await deletePost(newId, "wrong"), "wrong-password");
    assert.ok(await getPost(newId));
  });

  await check("글을 삭제하면 댓글도 함께 지워진다", async () => {
    await createComment({
      postId: newId,
      author: "댓글러",
      password: "cm1234",
      content: "함께 지워질 댓글",
    });
    assert.equal((await listComments(newId)).length, 1);

    assert.equal(await deletePost(newId, "pw1234"), "ok");
    assert.equal(await getPost(newId), null);
    // 외래 키의 ON DELETE CASCADE 확인
    assert.equal((await listComments(newId)).length, 0);
  });

  await check("없는 글 삭제는 not-found", async () => {
    assert.equal(await deletePost("p-nope", "pw1234"), "not-found");
  });

  /* ---- 페이지네이션 ---- */
  await check("페이지네이션이 범위를 벗어나지 않는다", async () => {
    await Promise.all(
      Array.from({ length: 5 }, (_, i) =>
        createPost({
          category: "free",
          title: `${MARK} 페이지 ${i}`,
          content: `본문 ${MARK}`,
          author: "테스터",
          password: "pw1234",
        }),
      ),
    );

    const page1 = await listPosts({ q: MARK, perPage: 2 });
    assert.equal(page1.total, 5);
    assert.equal(page1.totalPages, 3);
    assert.equal(page1.items.length, 2);

    const page3 = await listPosts({ q: MARK, perPage: 2, page: 3 });
    assert.equal(page3.items.length, 1);

    // 범위를 넘는 페이지 번호는 마지막 페이지로 보정된다
    const over = await listPosts({ q: MARK, perPage: 2, page: 99 });
    assert.equal(over.page, 3);

    // 페이지가 겹치지 않는다
    const page2 = await listPosts({ q: MARK, perPage: 2, page: 2 });
    const ids = [...page1.items, ...page2.items, ...page3.items].map(
      (p) => p.id,
    );
    assert.equal(new Set(ids).size, 5);
  });

  /* ---- 동시 쓰기 ---- */
  await check("동시 작성 요청이 유실되지 않는다", async () => {
    const before = (await listPosts({ q: MARK })).total;
    await Promise.all(
      Array.from({ length: 10 }, (_, i) =>
        createPost({
          category: "free",
          title: `${MARK} 동시 ${i}`,
          content: `본문 ${MARK}`,
          author: "테스터",
          password: "pw1234",
        }),
      ),
    );
    assert.equal((await listPosts({ q: MARK })).total, before + 10);
  });

  console.log(`\n통과: ${passed}건`);
} finally {
  const removed = await cleanup();
  console.log(`정리: 테스트 글 ${removed}건 삭제`);
}
