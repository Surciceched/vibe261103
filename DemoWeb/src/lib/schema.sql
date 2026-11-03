-- DemoWeb 게시판 스키마 (PostgreSQL / Neon)
-- 여러 번 실행해도 안전하다.

CREATE TABLE IF NOT EXISTS posts (
  id            TEXT PRIMARY KEY,
  category      TEXT        NOT NULL,
  title         TEXT        NOT NULL,
  content       TEXT        NOT NULL,
  author        TEXT        NOT NULL,
  password_hash TEXT        NOT NULL,
  views         INTEGER     NOT NULL DEFAULT 0,
  pinned        BOOLEAN     NOT NULL DEFAULT FALSE,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT posts_category_check
    CHECK (category IN ('notice', 'free', 'qna', 'dev'))
);

CREATE TABLE IF NOT EXISTS comments (
  id            TEXT PRIMARY KEY,
  -- 글이 지워지면 댓글도 함께 지워진다.
  post_id       TEXT        NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
  author        TEXT        NOT NULL,
  password_hash TEXT        NOT NULL,
  content       TEXT        NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 목록 정렬(최신순)과 카테고리 필터
CREATE INDEX IF NOT EXISTS posts_created_at_idx ON posts (created_at DESC);
CREATE INDEX IF NOT EXISTS posts_category_idx   ON posts (category);
CREATE INDEX IF NOT EXISTS posts_pinned_idx     ON posts (pinned);

-- 글별 댓글 조회·집계
CREATE INDEX IF NOT EXISTS comments_post_id_idx ON comments (post_id, created_at);
