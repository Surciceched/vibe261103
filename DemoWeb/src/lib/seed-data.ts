import type { CategoryValue } from "@/lib/types";

/** 예시 데이터. 비밀번호는 모두 아래 값으로 설정된다. */
export const SEED_PASSWORD = "1234";

export type SeedPost = {
  id: string;
  category: CategoryValue;
  title: string;
  content: string;
  author: string;
  views: number;
  pinned: boolean;
  /** 지금으로부터 몇 분 전에 작성된 글인지 */
  minutesAgo: number;
};

export type SeedComment = {
  id: string;
  postId: string;
  author: string;
  content: string;
  minutesAgo: number;
};

export const SEED_POSTS: SeedPost[] = [
  {
    id: "p-notice-rules",
    category: "notice",
    title: "게시판 이용 안내",
    content:
      "이 게시판은 로그인 없이 누구나 글을 쓸 수 있습니다.\n\n글을 쓸 때 입력한 비밀번호로 수정과 삭제를 할 수 있으니 잊지 마세요. 예시 글의 비밀번호는 모두 1234입니다.\n\n- 서로 존중하는 표현을 사용해 주세요.\n- 광고와 도배는 예고 없이 삭제됩니다.",
    author: "관리자",
    views: 128,
    pinned: true,
    minutesAgo: 60 * 24 * 7,
  },
  {
    id: "p-dev-next16",
    category: "dev",
    title: "Next.js 16 서버 액션으로 폼 처리하기",
    content:
      "서버 액션을 쓰면 API 라우트를 따로 만들지 않고 폼을 바로 서버에서 처리할 수 있습니다.\n\n주의할 점은 서버 액션이 UI를 거치지 않고 POST 요청으로도 호출될 수 있다는 것입니다. 그래서 권한 검사와 입력 검증을 액션 안에서 반드시 해야 합니다.\n\n이 게시판도 모든 쓰기 작업을 서버 액션에서 zod로 검증한 뒤 처리합니다.",
    author: "민수",
    views: 86,
    pinned: false,
    minutesAgo: 60 * 30,
  },
  {
    id: "p-qna-ts-generic",
    category: "qna",
    title: "타입스크립트 제네릭 제약 조건이 헷갈립니다",
    content:
      "extends를 붙이는 제네릭 제약이 언제 필요한지 감이 잘 안 옵니다.\n\n함수 안에서 인자의 속성에 접근해야 할 때만 제약을 주면 되는 걸까요? 아니면 미리 넓게 걸어두는 편이 좋을까요? 실무 기준이 궁금합니다.",
    author: "지현",
    views: 52,
    pinned: false,
    minutesAgo: 60 * 8,
  },
  {
    id: "p-free-desk",
    category: "free",
    title: "책상 정리하고 나니 집중이 잘 되네요",
    content:
      "모니터 한 대를 치우고 키보드만 남겼습니다. 화면이 줄어서 불편할 줄 알았는데 오히려 한 번에 한 가지만 보게 되어 좋습니다.\n\n여러분은 모니터 몇 대 쓰시나요?",
    author: "현우",
    views: 41,
    pinned: false,
    minutesAgo: 60 * 3,
  },
  {
    id: "p-dev-shadcn",
    category: "dev",
    title: "shadcn/ui는 라이브러리가 아니라 복사본입니다",
    content:
      "npm 패키지로 설치해 쓰는 컴포넌트 라이브러리와 달리, shadcn/ui는 소스를 프로젝트 안으로 복사해 넣습니다.\n\n그래서 버전 업그레이드가 자동으로 되지 않지만, 대신 컴포넌트를 마음대로 고칠 수 있습니다. 디자인을 많이 손봐야 하는 프로젝트에 잘 맞습니다.",
    author: "민수",
    views: 73,
    pinned: false,
    minutesAgo: 60 * 2,
  },
  {
    id: "p-qna-deploy",
    category: "qna",
    title: "정적 배포와 서버 배포 중 어떤 걸 골라야 할까요",
    content:
      "개인 프로젝트라 비용을 최소화하고 싶은데, 서버 액션을 쓰면 정적 배포가 안 되는 걸로 알고 있습니다.\n\n데이터를 저장하는 기능이 꼭 필요하면 서버가 있는 환경으로 가야 하나요?",
    author: "서연",
    views: 19,
    pinned: false,
    minutesAgo: 45,
  },
  {
    id: "p-free-welcome",
    category: "free",
    title: "처음 글 남겨봅니다",
    content: "조용히 보고만 있었는데 용기 내어 인사드립니다. 잘 부탁드립니다!",
    author: "하늘",
    views: 7,
    pinned: false,
    minutesAgo: 12,
  },
];

export const SEED_COMMENTS: SeedComment[] = [
  {
    id: "c-1",
    postId: "p-dev-next16",
    author: "지현",
    content: "검증을 액션 안에서 한다는 부분이 특히 도움이 됐습니다.",
    minutesAgo: 60 * 25,
  },
  {
    id: "c-2",
    postId: "p-dev-next16",
    author: "현우",
    content: "zod 스키마를 폼과 액션에서 같이 쓰면 중복이 줄어들더군요.",
    minutesAgo: 60 * 20,
  },
  {
    id: "c-3",
    postId: "p-qna-ts-generic",
    author: "민수",
    content:
      "속성에 접근해야 할 때 그때 좁히는 쪽을 권합니다. 미리 넓게 걸면 호출부가 불편해집니다.",
    minutesAgo: 60 * 6,
  },
  {
    id: "c-4",
    postId: "p-free-desk",
    author: "서연",
    content: "저는 두 대 쓰는데 한 대로 줄여볼까 고민되네요.",
    minutesAgo: 60 * 2,
  },
];
