"""
llm.py — Google AI Studio(Gemini) 무료 API 호출을 한 곳에 모아둔 래퍼.

- GEMINI_API_KEY 환경변수만 있으면 별도 설정 없이 동작.
  키 발급: https://aistudio.google.com/apikey (신용카드 필요 없음)
- 무료 티어는 Flash / Flash-Lite 계열만 지원되고 분당 요청 수(RPM) 제한이 있음.
  이 프로젝트는 매 턴마다 NPC 수 x (행동결정 + 대화턴) 만큼 호출이 쌓이므로
  기본값을 Flash-Lite로 잡았다. 무료 한도는 수시로 바뀌니 데모 전에
  https://ai.google.dev/gemini-api/docs/pricing 에서 최신 여부를 한 번 확인할 것.
- 429(rate limit) 에러가 나면 잠깐 쉬었다가 자동으로 한 번 재시도한다.
"""

import os
import re
import json
import time

from google import genai
from google.genai import types

MODEL = "gemini-3.1-flash-lite"  # 대안: "gemini-3.1-flash-lite" / "gemini-flash-latest" (더 빠르고 저렴할 수 있음, 발급받은 키의 지역/등급에 따라 사용 가능 여부가 다를 수 있어 안전한 값으로 기본 설정)

_client = None


def get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY 환경변수가 없습니다. "
                "https://aistudio.google.com/apikey 에서 무료로 발급받은 뒤 "
                "export GEMINI_API_KEY=... 실행하고 다시 시도하세요."
            )
        _client = genai.Client(api_key=api_key)
    return _client


def call_llm(system_prompt: str, user_prompt: str, max_tokens: int = 250, temperature: float = 0.9) -> str:
    """system/user 프롬프트를 보내고 텍스트만 돌려주는 헬퍼.

    temperature 기본값을 0.9로 높게 잡은 이유: 낮으면 NPC들이 매 턴 비슷한
    행동/대사만 반복해서 데모가 지루해짐.
    """
    client = get_client()
    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        temperature=temperature,
        max_output_tokens=max_tokens,
    )

    for attempt in range(2):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=user_prompt,
                config=config,
            )
            return (response.text or "").strip()
        except Exception as e:
            is_rate_limit = "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e)
            if is_rate_limit and attempt == 0:
                time.sleep(5)  # 무료 티어 RPM 제한 대비 짧게 대기 후 1회 재시도
                continue
            raise

    return ""  # 방어적 처리 (이론상 도달하지 않음)


def parse_json_safely(raw: str) -> dict:
    """LLM이 ```json 코드펜스를 붙이거나 잡담을 섞어도 최대한 파싱."""
    cleaned = re.sub(r"^```(json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        return {"action": raw[:80], "dialogue": "", "move_to": None}
