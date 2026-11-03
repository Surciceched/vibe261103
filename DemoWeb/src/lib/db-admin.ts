import { readFile } from "node:fs/promises";
import path from "node:path";

import { query } from "@/lib/db";
import { hashPassword } from "@/lib/password";
import { SEED_COMMENTS, SEED_PASSWORD, SEED_POSTS } from "@/lib/seed-data";

/**
 * 스키마 적용과 예시 데이터 적재. 앱 런타임이 아니라 scripts/에서 호출한다.
 */

const SCHEMA_PATH = path.join(process.cwd(), "src", "lib", "schema.sql");

/** schema.sql을 문장 단위로 끊어 순서대로 실행한다. */
export async function applySchema(): Promise<number> {
  const raw = await readFile(SCHEMA_PATH, "utf8");

  const statements = raw
    .split("\n")
    .filter((line) => !line.trim().startsWith("--"))
    .join("\n")
    .split(";")
    .map((s) => s.trim())
    .filter(Boolean);

  for (const statement of statements) {
    await query(statement);
  }

  return statements.length;
}

export async function dropSchema(): Promise<void> {
  // comments가 posts를 참조하므로 CASCADE로 함께 지운다.
  await query(`DROP TABLE IF EXISTS comments CASCADE`);
  await query(`DROP TABLE IF EXISTS posts CASCADE`);
}

export async function countPosts(): Promise<number> {
  const [{ count }] = await query<{ count: number | string }>(
    `SELECT COUNT(*)::int AS count FROM posts`,
  );
  return Number(count);
}

/** 예시 글·댓글을 넣는다. 같은 id가 있으면 건너뛴다. */
export async function seedDatabase(): Promise<{
  posts: number;
  comments: number;
}> {
  const passwordHash = await hashPassword(SEED_PASSWORD);
  const ago = (minutes: number) =>
    new Date(Date.now() - minutes * 60_000).toISOString();

  for (const post of SEED_POSTS) {
    await query(
      `INSERT INTO posts
         (id, category, title, content, author, password_hash, views, pinned, created_at, updated_at)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $9)
       ON CONFLICT (id) DO NOTHING`,
      [
        post.id,
        post.category,
        post.title,
        post.content,
        post.author,
        passwordHash,
        post.views,
        post.pinned,
        ago(post.minutesAgo),
      ],
    );
  }

  for (const comment of SEED_COMMENTS) {
    await query(
      `INSERT INTO comments (id, post_id, author, password_hash, content, created_at)
       VALUES ($1, $2, $3, $4, $5, $6)
       ON CONFLICT (id) DO NOTHING`,
      [
        comment.id,
        comment.postId,
        comment.author,
        passwordHash,
        comment.content,
        ago(comment.minutesAgo),
      ],
    );
  }

  return { posts: SEED_POSTS.length, comments: SEED_COMMENTS.length };
}
