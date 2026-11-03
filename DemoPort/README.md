# DemoPort — 개발자 프로필 웹사이트

`prd.md`의 요구사항을 구현한 정적 사이트입니다. 빌드 과정과 외부 의존성이 없습니다.

## 실행

`fetch`로 `data/projects.json`을 읽기 때문에 `file://`로 직접 열면 프로젝트 섹션이 비어 있습니다.
정적 서버로 실행하세요.

```bash
cd DemoPort
python -m http.server 8000
# http://localhost:8000
```

## 구조

```
DemoPort/
├── index.html              단일 페이지 (Hero · About · Skills · Projects · Experience · Contact)
├── 404.html
├── css/style.css           디자인 토큰 + 전체 스타일 (다크/라이트)
├── js/main.js              테마, 내비, 스크롤 스파이, 프로젝트 필터, 이메일 복사
├── data/projects.json      프로젝트 콘텐츠 ← 여기만 고치면 카드가 바뀝니다
├── assets/                 프로필·썸네일·파비콘·OG 이미지 (모두 SVG 자리표시자)
├── sitemap.xml, robots.txt
└── prd.md
```

## 교체해야 할 자리표시자

| 위치 | 현재 값 | 바꿀 내용 |
| --- | --- | --- |
| `index.html` 전역 | `홍길동` | 표시할 이름 (title, OG, JSON-LD, 헤더, Hero, 푸터) |
| `index.html` 전역 | `https://example.com/` | 실제 도메인 (canonical, OG, JSON-LD) |
| `index.html` About | `경력 N년` | 실제 연차 |
| `index.html` Contact · JSON-LD | `your-id` | GitHub / LinkedIn / App Store 계정 |
| `index.html` Experience | `소속 회사` | 실제 회사명과 성과 |
| `data/projects.json` | 샘플 6건 | 실제 프로젝트 (아래 스키마 참고) |
| `assets/profile.svg` | SVG 자리표시자 | 프로필 사진 (WebP 권장, 640×640 이상) |
| `assets/thumb-*.svg` | SVG 자리표시자 | 프로젝트 스크린샷 (16:9) |
| `assets/resume.pdf` | **없음** | 이력서 PDF — 넣지 않으면 About의 다운로드 버튼이 404 |
| `sitemap.xml`, `robots.txt` | `example.com` | 실제 도메인 |

이름을 한 번에 바꾸려면:

```bash
sed -i 's/홍길동/실제이름/g; s|https://example.com|https://내도메인|g' index.html 404.html sitemap.xml robots.txt
```

## projects.json 스키마

```jsonc
{
  "id": "slug",                     // 고유값
  "title": "프로젝트 이름",
  "category": "python" | "web" | "ios",   // 필터 버튼과 연결됨
  "summary": "한두 문장 요약",
  "role": "담당 역할",
  "tech": ["Swift", "SwiftUI"],
  "thumbnail": "assets/thumb-ios.svg",    // 생략 가능
  "links": [{ "label": "GitHub", "url": "https://..." }]
}
```

`category`를 새로 추가하려면 `index.html`의 필터 버튼(`data-filter`)과 `js/main.js`의
`KIND_LABEL`에 같은 키를 더하면 됩니다. 카드 내용은 모두 이스케이프 처리하며, 링크는
`http(s)` / `mailto` / 상대경로만 허용합니다.

## 구현된 요구사항

- **Hero** 이름·직함·CTA 2개(프로젝트 보기 / 이메일 문의), 주력 스택 배지
- **About** 프로필 이미지, 소개문, 요약 정보, 이력서 다운로드 버튼
- **Skills** Python / HTML5·Web / iOS 3그룹, 숙련도 라벨(주력·능숙·경험 있음) — 퍼센트 막대 미사용
- **Projects** JSON 기반 카드 그리드(3/2/1열), 분야 필터, 역할·기술·링크 표기
- **Experience** 수직 타임라인
- **Contact** mailto 링크 + 주소 복사 버튼, 외부 링크 3종 (문의 폼은 PRD대로 v1 제외)
- **공통** 다크/라이트 토글(localStorage 저장, 기본은 OS 설정), 스크롤 스파이 내비, 스크롤 진행 바,
  모바일 햄버거 메뉴, 404 페이지, 스킵 링크, 인쇄 스타일
- **SEO** 시맨틱 마크업, meta description, Open Graph, JSON-LD(Person), sitemap, robots
- **접근성** 키보드 전체 조작, `:focus-visible` 표시, `aria-pressed`/`aria-expanded`/`aria-live`,
  명암비 AA 이상, `prefers-reduced-motion` 및 `forced-colors` 대응

## 배포

**GitHub Pages**: 저장소에 올린 뒤 Settings → Pages → Branch `master` / 루트 선택.
루트가 `DemoPort/`라면 해당 폴더를 저장소 루트로 올리거나 Pages 경로를 맞추세요.

**Netlify**: 폴더를 끌어다 놓거나 저장소 연결 — 빌드 명령 없음, 배포 디렉터리는 루트.
`404.html`은 양쪽 모두 자동 인식합니다.

## 품질 점검 체크리스트

- [ ] Lighthouse 모바일 성능·접근성 90점 이상
- [ ] 키보드만으로 모든 링크·버튼 도달
- [ ] 360px / 768px / 1200px 레이아웃 확인
- [ ] 다크·라이트 양쪽에서 명암비 확인
- [ ] iOS Safari 실기기 확인
