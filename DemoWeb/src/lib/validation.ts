import { z } from "zod";

import { CATEGORY_VALUES } from "@/lib/types";

const author = z
  .string()
  .trim()
  .min(2, "이름은 2자 이상 입력해 주세요.")
  .max(20, "이름은 20자까지 입력할 수 있습니다.");

const password = z
  .string()
  .min(4, "비밀번호는 4자 이상 입력해 주세요.")
  .max(64, "비밀번호는 64자까지 입력할 수 있습니다.");

export const postSchema = z.object({
  category: z.enum(CATEGORY_VALUES, { message: "분류를 선택해 주세요." }),
  title: z
    .string()
    .trim()
    .min(2, "제목은 2자 이상 입력해 주세요.")
    .max(100, "제목은 100자까지 입력할 수 있습니다."),
  content: z
    .string()
    .trim()
    .min(5, "내용은 5자 이상 입력해 주세요.")
    .max(5000, "내용은 5000자까지 입력할 수 있습니다."),
  author,
  password,
});

export const postUpdateSchema = postSchema.omit({ author: true });

export const commentSchema = z.object({
  author,
  password,
  content: z
    .string()
    .trim()
    .min(2, "댓글은 2자 이상 입력해 주세요.")
    .max(500, "댓글은 500자까지 입력할 수 있습니다."),
});

export const passwordOnlySchema = z.object({ password });

export type FieldErrors = Record<string, string[] | undefined>;

/** 서버 액션이 폼으로 돌려주는 상태 */
export type FormState = {
  status: "idle" | "error";
  message?: string;
  fieldErrors?: FieldErrors;
  /** 입력값 유지용 (비밀번호는 담지 않는다) */
  values?: Record<string, string>;
};

export const IDLE_STATE: FormState = { status: "idle" };

export function toErrorState(
  error: z.ZodError,
  values?: Record<string, string>,
): FormState {
  const flat = z.flattenError(error);
  return {
    status: "error",
    message: "입력한 내용을 다시 확인해 주세요.",
    fieldErrors: flat.fieldErrors as FieldErrors,
    values,
  };
}

export function errorState(
  message: string,
  fieldErrors?: FieldErrors,
  values?: Record<string, string>,
): FormState {
  return { status: "error", message, fieldErrors, values };
}
