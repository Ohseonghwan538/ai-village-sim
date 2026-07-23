# AI 마을 시뮬레이션 — 스타터 킷 (Gemini + 실시간 애니메이션)

RAG · 하네스 · 에이전틱 · 시뮬레이션을 한 프로젝트에서 보여주기 위한 뼈대 코드.
2~3명의 AI NPC가 각자 성격과 기억을 갖고 마을에서 살아가는 미니 시뮬레이션이다
(스탠퍼드 Generative Agents/"스몰빌" 논문에서 착안). **Google AI Studio 무료 API**로
동작하고, 지도 위에서 NPC가 실제로 움직이는 걸 볼 수 있다.

> Streamlit 대신 Flask + 순수 HTML/CSS/JS로 프론트를 만든 이유: Streamlit은
> 상호작용마다 화면을 통째로 다시 그려서 부드러운 이동 애니메이션을 만들기 어렵다.
> 여기서는 브라우저 JS가 NPC 마커의 좌표(left/top)만 바꾸고 나머지 DOM은
> 그대로 두기 때문에 CSS transition으로 실제로 "움직이는" 느낌을 낼 수 있다.

이 코드는 **끝난 결과물이 아니라 시작점**이다. 그대로 실행해도 돌아가지만,
남은 시간에 6번 섹션을 참고해서 직접 확장해야 진짜 "내가 만든 것"이 된다.

---

## 1. 빠른 시작 (로컬)

```bash
pip install -r requirements.txt

# 1) 무료 API 키 발급: https://aistudio.google.com/apikey (신용카드 불필요, 구글 계정만 있으면 됨)
# 2) 환경변수로 등록
export GEMINI_API_KEY=발급받은키   # Windows PowerShell: $env:GEMINI_API_KEY="발급받은키"

python test_offline.py   # (선택) API 호출 없이 로직만 5초 안에 검증
python app.py             # http://127.0.0.1:5000 접속 -> 지도가 보이면 성공
```

브라우저에서 "다음 턴 ▶"을 누르면 NPC가 실제로 위치를 바꾸며 지도 위를 이동한다.
"자동재생"을 켜면 몇 초 간격으로 알아서 턴이 진행된다.

Python 3.10 이상 필요.

---

## 2. 파일 구조 & 4대 요소 매핑

발표할 때 이 표 그대로 설명하면 된다.

| 파일 | 담당 | 설명 |
|---|---|---|
| `village.py` | **하네스 + 시뮬레이션** | `run_tick()`이 매 턴마다 모든 NPC의 perceive→plan→act를 순서대로 실행하는 스케줄러. `scripted_events()`가 마을에 주입되는 이벤트(=시뮬레이션 시나리오) |
| `memory.py` | **RAG** | `MemoryStream.retrieve()`가 recency(최근성)+importance(중요도)+relevance(관련성) 가중합으로 관련 기억을 검색해 프롬프트에 주입 |
| `npc.py` | **에이전틱** | `decide_action()` / `speak()`가 검색된 기억을 근거로 다음 행동·대사를 스스로 계획 |
| `llm.py` | (공통) | Gemini API 호출을 한 곳에 모은 래퍼 |
| `app.py` | 웹 서버 | `/api/state`, `/api/tick`, `/api/reset` 세 개의 엔드포인트만 있는 Flask 백엔드 |
| `templates/index.html`, `static/app.js`, `static/style.css` | 프론트엔드 | 지도 렌더링 + 폴링 + 이동 애니메이션 |
| `main.py`, `test_offline.py` | CLI | 콘솔에서 텍스트로만 보고 싶을 때(main.py), API 키 없이 로직만 검증할 때(test_offline.py) |

---

## 3. 이미 검증된 것

- `test_offline.py`(가짜 응답 목업)로 하네스/RAG/이벤트 로직에 버그 없는 걸 확인했고,
  `memory.py`의 검색 랭킹도 "정전 관련 기억을 물으면 정전 기억이 1등으로 나오는지" 따로 확인함.
- Flask 엔드포인트 3개(`/api/state`, `/api/tick`, `/api/reset`) 전부 목업 LLM으로 왕복 테스트 완료.
- `GEMINI_API_KEY`가 없을 때 서버가 죽지 않고 JSON 에러를 반환하는 것도 확인 (프론트에서 빨간 에러 박스로 표시됨).
- `gunicorn app:app`로 실제 프로덕션 서버 구동까지 확인함 (배포 시 이 명령을 그대로 씀).

즉 이 위에 쌓는 코드에만 집중하면 된다. 실제 대사 퀄리티·애니메이션 느낌은
API 키 넣고 `python app.py`로 직접 브라우저에서 봐야 한다 (목업은 흉내만 냄).

---

## 4. Gemini 무료 티어 관련 주의사항

- 무료 티어는 **Flash / Flash-Lite 계열만** 지원되고 분당 요청 수(RPM) 제한이 있다
  (대략 Flash 15RPM, Flash-Lite 30RPM 수준, 수시로 바뀔 수 있음).
- 이 프로젝트는 한 틱마다 NPC 수 x (행동결정 + 대화턴) 만큼 호출이 쌓인다. NPC 3명 기준
  한 틱에 API 호출이 5~6번 정도 나갈 수 있으니, 자동재생을 너무 빠르게 돌리면 429(rate limit)
  에러를 만날 수 있다. `llm.py`에 429 발생 시 5초 대기 후 1회 자동 재시도하는 로직을 넣어뒀지만,
  그래도 계속 걸리면 `static/app.js`의 자동재생 대기시간(`setTimeout(doTick, 1500)`)을 늘릴 것.
- 데모 직전에 https://ai.google.dev/gemini-api/docs/pricing 에서 현재 무료 모델 목록을
  한 번 확인하는 걸 추천 (모델 이름이 자주 바뀜). `llm.py` 상단의 `MODEL` 상수만 바꾸면 됨.

---

## 5. GitHub에 올리기

로컬에 git 저장소는 이미 초기화·커밋까지 해뒀다. 본인 GitHub 계정에 올리려면:

```bash
# GitHub에서 새 저장소를 먼저 만든 다음 (Add README 체크 해제하고 빈 저장소로 생성)
git remote add origin https://github.com/본인아이디/저장소이름.git
git branch -M main
git push -u origin main
```

**주의**: `.gitignore`에 `.env`가 이미 포함되어 있어서 API 키가 실수로 커밋되진 않는다.
`GEMINI_API_KEY`는 절대 코드에 하드코딩하지 말고 항상 환경변수로만 다룰 것.

---

## 6. 웹 배포 (Render, 무료)

Streamlit Cloud 대신 Flask 앱이므로 **Render**를 추천 (GitHub 연동, 무료 티어, 신용카드 불필요).

1. https://render.com 가입 후 "New +" → "Web Service" → 방금 push한 GitHub 저장소 선택
2. 설정값:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
3. "Environment" 탭에서 `GEMINI_API_KEY` 환경변수를 등록 (여기에만 실제 키를 넣는다, 절대 코드/저장소에는 넣지 않음)
4. Deploy — 몇 분 후 `https://저장소이름.onrender.com` 같은 공개 URL이 생김

무료 티어 특성상 일정 시간 요청이 없으면 서버가 잠들고, 다음 요청 때 첫 응답이
몇 초~수십 초 느릴 수 있다 (콜드 스타트). 발표 직전에 한 번 미리 접속해서
깨워두면 데모 중 어색한 로딩을 피할 수 있다.

(대안: PythonAnywhere도 무료 티어로 Flask를 지원하고 브라우저에서 바로 설정 가능해서
Git/CLI가 부담스러우면 이쪽이 더 쉬울 수 있음.)

---

## 7. 일부러 단순화한 부분 (알고 발표하면 오히려 좋은 점수 포인트)

- **RAG에 진짜 임베딩 대신 TF-IDF 사용**: 별도 임베딩 API 호출이 필요 없고 빠름.
  시간이 남으면 Gemini의 `text-embedding-004` 같은 임베딩 모델로 교체 가능 —
  `memory.py`의 `retrieve()` 내부만 바꾸면 나머지 구조는 그대로 재사용된다.
- **중요도 채점이 키워드 규칙 기반**: LLM 호출로 바꾸면 더 정교해지지만 호출 수가 늘어남.
- **리플렉션(reflection) 레이어 없음**: 원 논문에는 기억을 종합해 "나는 요즘 외로운 것
  같다" 같은 상위 통찰을 만드는 3단계가 있다. 아래 확장 아이디어 1번이 이거다.
- **NPC 이동은 한 턴 = 한 칸(jump-cut)**: 실제로는 목적지까지 여러 프레임에 걸쳐
  보간(interpolation)하는 게 아니라, 턴이 끝나면 다음 위치로 CSS transition을 태워
  "슥" 이동하는 방식. 실시간 게임처럼 프레임 단위로 걷는 애니메이션을 원하면
  `static/app.js`에 경로 보간 로직을 추가해야 하는데, 이건 난이도 대비 임팩트가
  낮아서(이미 "움직임이 보인다"는 요구사항은 충족) 스타터에는 넣지 않았다.

---

## 8. 남은 시간에 추가하면 좋은 것 (임팩트 순)

1. **리플렉션 추가** (~30분, 임팩트 큼): 몇 턴마다 최근 기억을 모아 LLM에게 "이 기억들을
   보고 한 문장으로 통찰을 뽑아줘"라고 요청하고, 결과를 importance 높은 기억으로 저장.
   지도 위 말풍선으로 "AI가 스스로 자기 상태를 깨닫는" 순간을 보여주면 반응이 좋을 것.
2. **관계 설정 + 4번째 NPC** (~20분): 예를 들어 "민준은 수아를 짝사랑한다"를 초기 기억으로
   미리 넣어두면 대화가 훨씬 풍부해짐. `main.py`/`app.py`의 `build_village()`만 수정.
3. **이벤트 랜덤화** (~30분): `scripted_events()`의 고정 딕셔너리 대신 매 틱마다 일정 확률로
   이벤트 풀에서 하나가 발생하도록 바꾸면 "돌릴 때마다 다른 이야기"가 된다.
4. **말풍선/이동 경로 꾸미기** (선택, ~20분): 지금은 대사가 3초 정도 떴다가 사라지는데,
   `static/style.css`의 `.npc-bubble`을 조정해 스타일을 더 다듬거나, 이동 중 발자국
   이펙트를 추가하는 정도는 저비용 고효율.

---

## 9. 데모 대본 (3분 기준)

- **0:00–0:30** — 파일 구조로 4대 요소 매핑 설명 (2번 섹션 표 그대로)
- **0:30–2:00** — 실제 배포된 URL(또는 로컬 화면)에서 "다음 턴"을 눌러 NPC가 지도 위에서
  실제로 움직이는 걸 보여줌. 이벤트가 뜨기 직전에 "지금 정전 이벤트가 주입됩니다"라고
  미리 예고하면 심사위원이 반응 포인트를 놓치지 않음
- **2:00–3:00** — NPC 한 명을 짚어서 "얘가 이 행동을 한 이유는 저장된 이 기억 때문"이라고
  설명 (원하면 `memory.retrieve()` 결과를 콘솔에 찍어서 같이 보여주면 RAG가 실제로
  판단에 쓰였다는 게 증명됨)

---

## 10. 자주 만나는 문제

- **"가만히 있는다"만 반복** → JSON 파싱 실패 가능성. `llm.py`의 `max_tokens`를 늘리거나
  시스템 프롬프트에 "JSON 외 텍스트 절대 금지"를 더 강하게 명시
- **429 에러가 자주 뜸** → 무료 티어 RPM 초과. `static/app.js`의 자동재생 간격을 늘리거나
  NPC 수를 줄이기
- **지도에서 NPC가 안 움직이는 것처럼 보임** → 브라우저 콘솔(F12)에서 에러 확인.
  `/api/tick` 응답이 200인데도 안 움직이면 `renderNpcs()`의 좌표 계산 로직을 점검
- **로컬은 되는데 Render에서 안 됨** → Render "Environment" 탭에 `GEMINI_API_KEY`를
  등록했는지, Start Command가 `gunicorn app:app`인지 확인
