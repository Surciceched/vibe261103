# DemoWeb — 웹 게시판

Next.js 16 (App Router) · TypeScript · shadcn/ui · Tailwind CSS 4 · **Neon(PostgreSQL)** 으로 만든
게시판입니다. 로그인 없이 글을 쓰고, 글을 쓸 때 입력한 비밀번호로 수정·삭제합니다.

## 설정

`.env.example`을 복사해 `.env.local`을 만들고 Neon 연결 문자열을 넣습니다.

```bash
cp .env.example .env.local
# DATABASE_URL="postgresql://<user>:<password>@<host>/<database>?sslmode=require"
```

`.env*`는 `.gitignore`에 걸려 있어 저장소에 올라가지 않습니다(`.env.example`만 예외).

## 실행

```bash
npm install          # 이미 설치되어 있으면 생략
npm run db:migrate   # 테이블·인덱스 생성 (여러 번 실행해도 안전)
npm run db:seed      # 예시 글 7건 · 댓글 4건
npm run dev          # http://localhost:3000
```

**예시 글과 댓글의 비밀번호는 모두 `1234`** 입니다.

| 명령 | 설명 |
| --- | --- |
| `npm run dev` | 개발 서버 |
| `npm run build` / `npm start` | 프로덕션 빌드·실행 |
| `npm run lint` | ESLint |
| `npm run typecheck` | `tsc --noEmit` |
| `npm run db:migrate` | 스키마 적용 (idempotent) |
| `npm run db:seed` | 예시 데이터 적재 (같은 id는 건너뜀) |
| `npm run db:reset` | **테이블 삭제 후** 재생성·재적재 |
| `npm run smoke` | 데이터 계층 스모크 테스트 30건 |
| `npx tsx scripts/add-sample-posts.mts 8` | 목록·페이지네이션 확인용 더미 글 |

## 데이터베이스

Neon의 HTTP 드라이버(`@neondatabase/serverless`)를 씁니다. 커넥션 풀을 직접 관리하지
않으므로 서버리스 환경에서도 연결이 남지 않습니다.

```
posts                                comments
├ id            TEXT PK              ├ id            TEXT PK
├ category      TEXT  CHECK(4종)     ├ post_id       TEXT FK → posts(id) ON DELETE CASCADE
├ title         TEXT                 ├ author        TEXT
├ content       TEXT                 ├ password_hash TEXT
├ author        TEXT                 ├ content       TEXT
├ password_hash TEXT                 └ created_at    TIMESTAMPTZ
├ views         INTEGER
├ pinned        BOOLEAN
├ created_at    TIMESTAMPTZ
└ updated_at    TIMESTAMPTZ
```

스키마 정의는 `src/lib/schema.sql`에 있습니다. 인덱스는 목록 정렬(`created_at DESC`),
카테고리 필터, 공지 고정, 글별 댓글 조회에 걸려 있습니다.

## 기능

**목록 (`/`)**
- 분류 필터(공지·자유·질문·개발), 제목·내용·작성자 검색
- 최신순 / 조회순 / 댓글순 정렬, 페이지당 10건 페이지네이션
- 공지 상단 고정 (검색 중에는 고정 해제)
- 데스크톱은 표, 모바일은 카드 레이아웃

**상세 (`/posts/[id]`)**
- 조회수(같은 세션에서 중복 집계 안 함), 작성·수정 시각
- 이전 글 / 다음 글 이동
- 댓글 목록·작성·삭제

**작성·수정·삭제**
- `/posts/new`, `/posts/[id]/edit`
- 수정·삭제 시 비밀번호 확인, 글 삭제 시 댓글 함께 삭제(외래 키 CASCADE)

**공통**
- 다크/라이트 테마 토글(시스템 설정 기본값)
- 404 / 에러 / 로딩 화면, 토스트 알림

## 구조

```
src/
├── app/
│   ├── layout.tsx                헤더·푸터·테마·토스트
│   ├── page.tsx                  목록 셸 (+ Suspense)
│   ├── loading.tsx  error.tsx  not-found.tsx
│   └── posts/
│       ├── new/page.tsx
│       └── [id]/
│           ├── page.tsx          상세 셸 (+ Suspense)
│           ├── post-detail.tsx   상세 본문 (params를 여기서 await)
│           └── edit/
│               ├── page.tsx
│               └── edit-form.tsx
├── components/
│   ├── ui/                       shadcn/ui 컴포넌트 (17개)
│   ├── site-header.tsx  theme-provider.tsx  theme-toggle.tsx
│   ├── board-content.tsx         목록 본문 (searchParams를 여기서 await)
│   ├── board-toolbar.tsx  post-list.tsx  board-pagination.tsx
│   ├── board-skeleton.tsx        Suspense 폴백
│   ├── post-form.tsx             작성·수정 공용 폼
│   ├── comment-section.tsx  comment-form.tsx
│   ├── delete-post-dialog.tsx  delete-comment-dialog.tsx
│   └── view-tracker.tsx
└── lib/
    ├── db.ts                     Neon 접속 + 파라미터 바인딩 질의
    ├── schema.sql                테이블·인덱스 정의
    ├── db-admin.ts               스키마 적용·예시 데이터 (스크립트 전용)
    ├── seed-data.ts              예시 글·댓글 원본
    ├── posts.ts                  조회·생성·수정·삭제 (SQL)
    ├── actions.ts                서버 액션 ("use server")
    ├── validation.ts             zod 스키마 + 폼 상태
    ├── types.ts  query.ts  format.ts  password.ts
```

## 설계 메모

**SQL은 항상 파라미터로 바인딩합니다.** 문자열을 이어 붙여 값을 넣지 않습니다. 검색은
`ILIKE` 대신 `POSITION(LOWER($2) IN LOWER(...))`을 써서 검색어의 `%`, `_`를 따로
이스케이프할 필요가 없게 했습니다. 정렬 기준은 화이트리스트(`ORDER_BY` 맵)에서만 고릅니다.

**비밀번호는 scrypt로 해시**해 저장하고 `timingSafeEqual`로 비교합니다. 조회 질의는
`password_hash`를 아예 선택하지 않으므로 해시가 클라이언트로 넘어가지 않습니다.

**서버 액션은 UI를 거치지 않고 POST로도 호출될 수 있으므로**, 모든 입력을 액션 안에서
zod로 다시 검증합니다. 분류 값을 위조해 보내도 `z.enum`과 DB의 `CHECK` 제약에서 걸립니다.

**페이지는 셸과 데이터 영역으로 나눠 두었습니다.** 이 버전은 Cache Components와 PPR이
기본이라, `params`/`searchParams`를 페이지 최상단에서 await하면 셸이 URL에 묶여
"uncached data during prerendering" 경고가 납니다. 그래서 프로미스를 `<Suspense>` 안의
자식 컴포넌트로 내려, 껍데기는 정적으로 남고 데이터 영역만 요청마다 스트리밍됩니다.

**폼은 자바스크립트가 없어도 동작합니다.** `useActionState` + `<form action={...}>`
조합이라 JS 실행 전에도 제출이 처리됩니다. 단, 대화상자(삭제 확인)는 JS가 필요합니다.

**조회수는 렌더링 중에 올리지 않습니다.** `view-tracker.tsx`가 마운트 후 한 번 서버
액션을 호출하고, `sessionStorage`로 같은 세션의 중복 집계를 막습니다.

## 확인한 것

- `npm run build` 통과, `npm run typecheck`·`npm run lint` 경고 없음
- `npm run smoke` 30건 통과 — 검색·필터·정렬·페이지네이션 경계, 비밀번호 검증,
  글 삭제 시 댓글 CASCADE 삭제, 동시 작성 10건 유실 없음
- 개발 서버에서 전 경로 응답 확인, 서버 액션을 HTTP로 직접 호출해 분류 값 위조·검증 실패·
  비밀번호 불일치 거부와 정상 생성·수정·댓글·조회수 반영을 Neon 데이터로 확인

스모크 테스트는 `.env.local`의 DB를 그대로 쓰되, 제목에 고유 표식을 넣은 행만 만들고
끝나면 지웁니다. 기존 데이터는 읽기만 합니다.

브라우저에서 직접 클릭해 확인하지 않은 부분: 대화상자 열기·닫기, 토스트, 테마 토글의
시각적 동작.

## 운영 환경으로 옮길 때

- 비밀번호만으로 본인을 확인하므로 공개 게시판에는 도배·스팸 대응(요청 제한, 캡차)이
  추가로 필요합니다.
- 연결 문자열은 배포 플랫폼의 환경 변수로 넣으세요. 저장소에 커밋하지 않습니다.
- Neon 무료 플랜은 유휴 시 컴퓨트가 멈춥니다. 첫 요청이 수백 ms 느릴 수 있습니다.
