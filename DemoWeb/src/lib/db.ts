import { neon, type NeonQueryFunction } from "@neondatabase/serverless";

/**
 * Neon(PostgreSQL) 접속.
 *
 * HTTP 기반 드라이버라 커넥션 풀을 직접 관리하지 않는다. 서버리스 환경에서도
 * 연결이 남지 않으며, 요청마다 새 연결을 맺는 비용도 없다.
 */

let cached: NeonQueryFunction<false, false> | null = null;

export function getSql(): NeonQueryFunction<false, false> {
  if (cached) return cached;

  const url = process.env.DATABASE_URL;
  if (!url) {
    throw new Error(
      "DATABASE_URL이 설정되지 않았습니다. .env.example을 참고해 .env.local을 만들어 주세요.",
    );
  }

  cached = neon(url);
  return cached;
}

/**
 * 동적 조건이 붙는 질의용. 자리표시자($1, $2 …)와 값 배열을 그대로 넘긴다.
 * 문자열을 이어 붙여 값을 넣는 일은 하지 않는다(SQL 주입 방지).
 */
export async function query<T>(
  text: string,
  params: unknown[] = [],
): Promise<T[]> {
  const sql = getSql();
  const rows = await sql.query(text, params);
  return rows as T[];
}
