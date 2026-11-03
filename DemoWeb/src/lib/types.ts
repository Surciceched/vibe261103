/** 게시판 도메인 타입 */

export const CATEGORIES = [
  { value: "notice", label: "공지" },
  { value: "free", label: "자유" },
  { value: "qna", label: "질문" },
  { value: "dev", label: "개발" },
] as const;

export type CategoryValue = (typeof CATEGORIES)[number]["value"];

export const CATEGORY_VALUES = CATEGORIES.map((c) => c.value) as [
  CategoryValue,
  ...CategoryValue[],
];

export function categoryLabel(value: string): string {
  return CATEGORIES.find((c) => c.value === value)?.label ?? value;
}

export type Comment = {
  id: string;
  postId: string;
  author: string;
  /** scrypt 해시. 클라이언트로 내보내지 않는다. */
  passwordHash: string;
  content: string;
  createdAt: string;
};

export type Post = {
  id: string;
  category: CategoryValue;
  title: string;
  content: string;
  author: string;
  /** scrypt 해시. 클라이언트로 내보내지 않는다. */
  passwordHash: string;
  views: number;
  pinned: boolean;
  createdAt: string;
  updatedAt: string;
};

export type BoardData = {
  posts: Post[];
  comments: Comment[];
};

/** 비밀번호 해시를 제거한 공개용 형태 */
export type PublicPost = Omit<Post, "passwordHash"> & { commentCount: number };
export type PublicComment = Omit<Comment, "passwordHash">;

export type SortOrder = "latest" | "views" | "comments";

export type ListParams = {
  q?: string;
  category?: string;
  sort?: SortOrder;
  page?: number;
  perPage?: number;
};

export type ListResult = {
  items: PublicPost[];
  total: number;
  page: number;
  perPage: number;
  totalPages: number;
};
