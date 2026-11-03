import { randomUUID } from "node:crypto";

import { query } from "@/lib/db";
import { hashPassword, verifyPassword } from "@/lib/password";
import type {
  CategoryValue,
  ListParams,
  ListResult,
  PublicComment,
  PublicPost,
  SortOrder,
} from "@/lib/types";

export const DEFAULT_PER_PAGE = 10;

/* ---------------- 행 → 도메인 객체 ---------------- */

type PostRow = {
  id: string;
  category: CategoryValue;
  title: string;
  content: string;
  author: string;
  views: number;
  pinned: boolean;
  created_at: string | Date;
  updated_at: string | Date;
  comment_count: number | string;
};

type CommentRow = {
  id: string;
  post_id: string;
  author: string;
  content: string;
  created_at: string | Date;
};

function iso(value: string | Date): string {
  return value instanceof Date ? value.toISOString() : new Date(value).toISOString();
}

function toPost(row: PostRow): PublicPost {
  return {
    id: row.id,
    category: row.category,
    title: row.title,
    content: row.content,
    author: row.author,
    views: Number(row.views),
    pinned: row.pinned,
    createdAt: iso(row.created_at),
    updatedAt: iso(row.updated_at),
    commentCount: Number(row.comment_count),
  };
}

function toComment(row: CommentRow): PublicComment {
  return {
    id: row.id,
    postId: row.post_id,
    author: row.author,
    content: row.content,
    createdAt: iso(row.created_at),
  };
}

/**
 * 비밀번호 해시는 어떤 조회 함수도 선택하지 않는다.
 * 본인 확인이 필요한 곳에서만 별도로 읽는다.
 */
const POST_COLUMNS = `
  p.id, p.category, p.title, p.content, p.author, p.views, p.pinned,
  p.created_at, p.updated_at,
  (SELECT COUNT(*) FROM comments c WHERE c.post_id = p.id) AS comment_count
`;

/** 정렬 기준은 화이트리스트에서만 고른다(문자열 조합으로 들어오지 않게). */
const ORDER_BY: Record<SortOrder, string> = {
  latest: "p.created_at DESC, p.id DESC",
  views: "p.views DESC, p.created_at DESC",
  comments: "comment_count DESC, p.created_at DESC",
};

/* ---------------- 조회 ---------------- */

export async function listPosts(params: ListParams = {}): Promise<ListResult> {
  const q = params.q?.trim() || null;
  const category = params.category || null;
  const sort: SortOrder = params.sort ?? "latest";
  const perPage = params.perPage ?? DEFAULT_PER_PAGE;

  // ILIKE 대신 position()을 쓴다. 검색어의 %, _ 를 따로 이스케이프할 필요가 없다.
  const where = `
    WHERE ($1::text IS NULL OR p.category = $1)
      AND ($2::text IS NULL
           OR POSITION(LOWER($2) IN LOWER(p.title))   > 0
           OR POSITION(LOWER($2) IN LOWER(p.content)) > 0
           OR POSITION(LOWER($2) IN LOWER(p.author))  > 0)
  `;

  const [{ count }] = await query<{ count: number | string }>(
    `SELECT COUNT(*)::int AS count FROM posts p ${where}`,
    [category, q],
  );

  const total = Number(count);
  const totalPages = Math.max(1, Math.ceil(total / perPage));
  const page = Math.min(Math.max(1, params.page ?? 1), totalPages);

  // 공지 고정은 검색하지 않을 때만 적용한다.
  const pinnedFirst = q ? "" : "p.pinned DESC,";

  const rows = await query<PostRow>(
    `SELECT ${POST_COLUMNS}
       FROM posts p
       ${where}
      ORDER BY ${pinnedFirst} ${ORDER_BY[sort]}
      LIMIT $3 OFFSET $4`,
    [category, q, perPage, (page - 1) * perPage],
  );

  return { items: rows.map(toPost), total, page, perPage, totalPages };
}

export async function getPost(id: string): Promise<PublicPost | null> {
  const rows = await query<PostRow>(
    `SELECT ${POST_COLUMNS} FROM posts p WHERE p.id = $1`,
    [id],
  );
  return rows.length ? toPost(rows[0]) : null;
}

export async function listComments(postId: string): Promise<PublicComment[]> {
  const rows = await query<CommentRow>(
    `SELECT id, post_id, author, content, created_at
       FROM comments
      WHERE post_id = $1
      ORDER BY created_at ASC, id ASC`,
    [postId],
  );
  return rows.map(toComment);
}

export async function countByCategory(): Promise<Record<string, number>> {
  const rows = await query<{ category: string; count: number | string }>(
    `SELECT category, COUNT(*)::int AS count FROM posts GROUP BY category`,
  );
  return rows.reduce<Record<string, number>>((acc, row) => {
    acc[row.category] = Number(row.count);
    return acc;
  }, {});
}

export async function getNeighbors(id: string): Promise<{
  prev: { id: string; title: string } | null;
  next: { id: string; title: string } | null;
}> {
  const current = await query<{ created_at: string | Date }>(
    `SELECT created_at FROM posts WHERE id = $1`,
    [id],
  );
  if (!current.length) return { prev: null, next: null };

  const createdAt = iso(current[0].created_at);

  // (created_at, id) 튜플로 비교해 같은 시각의 글도 순서가 흔들리지 않는다.
  const [newer, older] = await Promise.all([
    query<{ id: string; title: string }>(
      `SELECT id, title FROM posts
        WHERE (created_at, id) > ($1, $2)
        ORDER BY created_at ASC, id ASC
        LIMIT 1`,
      [createdAt, id],
    ),
    query<{ id: string; title: string }>(
      `SELECT id, title FROM posts
        WHERE (created_at, id) < ($1, $2)
        ORDER BY created_at DESC, id DESC
        LIMIT 1`,
      [createdAt, id],
    ),
  ]);

  return {
    next: newer[0] ?? null,
    prev: older[0] ?? null,
  };
}

/* ---------------- 생성 / 수정 / 삭제 ---------------- */

export type CreatePostInput = {
  category: CategoryValue;
  title: string;
  content: string;
  author: string;
  password: string;
};

export async function createPost(input: CreatePostInput): Promise<string> {
  const id = `p-${randomUUID().slice(0, 8)}`;
  const passwordHash = await hashPassword(input.password);

  await query(
    `INSERT INTO posts (id, category, title, content, author, password_hash)
     VALUES ($1, $2, $3, $4, $5, $6)`,
    [
      id,
      input.category,
      input.title,
      input.content,
      input.author,
      passwordHash,
    ],
  );

  return id;
}

export type UpdatePostInput = {
  id: string;
  category: CategoryValue;
  title: string;
  content: string;
  password: string;
};

export type MutationOutcome = "ok" | "not-found" | "wrong-password";

/** 저장된 해시와 입력 비밀번호를 비교한다. */
async function authorize(
  table: "posts" | "comments",
  id: string,
  password: string,
): Promise<MutationOutcome> {
  const rows = await query<{ password_hash: string }>(
    `SELECT password_hash FROM ${table} WHERE id = $1`,
    [id],
  );
  if (!rows.length) return "not-found";
  return (await verifyPassword(password, rows[0].password_hash))
    ? "ok"
    : "wrong-password";
}

export async function updatePost(
  input: UpdatePostInput,
): Promise<MutationOutcome> {
  const allowed = await authorize("posts", input.id, input.password);
  if (allowed !== "ok") return allowed;

  await query(
    `UPDATE posts
        SET category = $2, title = $3, content = $4, updated_at = NOW()
      WHERE id = $1`,
    [input.id, input.category, input.title, input.content],
  );

  return "ok";
}

export async function deletePost(
  id: string,
  password: string,
): Promise<MutationOutcome> {
  const allowed = await authorize("posts", id, password);
  if (allowed !== "ok") return allowed;

  // comments.post_id의 ON DELETE CASCADE로 댓글도 함께 지워진다.
  await query(`DELETE FROM posts WHERE id = $1`, [id]);
  return "ok";
}

export async function checkPostPassword(
  id: string,
  password: string,
): Promise<MutationOutcome> {
  return authorize("posts", id, password);
}

export async function incrementViews(id: string): Promise<void> {
  await query(`UPDATE posts SET views = views + 1 WHERE id = $1`, [id]);
}

/* ---------------- 댓글 ---------------- */

export type CreateCommentInput = {
  postId: string;
  author: string;
  password: string;
  content: string;
};

export async function createComment(
  input: CreateCommentInput,
): Promise<MutationOutcome> {
  const exists = await query<{ id: string }>(
    `SELECT id FROM posts WHERE id = $1`,
    [input.postId],
  );
  if (!exists.length) return "not-found";

  const passwordHash = await hashPassword(input.password);

  await query(
    `INSERT INTO comments (id, post_id, author, password_hash, content)
     VALUES ($1, $2, $3, $4, $5)`,
    [
      `c-${randomUUID().slice(0, 8)}`,
      input.postId,
      input.author,
      passwordHash,
      input.content,
    ],
  );

  return "ok";
}

export async function deleteComment(
  id: string,
  password: string,
): Promise<MutationOutcome> {
  const allowed = await authorize("comments", id, password);
  if (allowed !== "ok") return allowed;

  await query(`DELETE FROM comments WHERE id = $1`, [id]);
  return "ok";
}
