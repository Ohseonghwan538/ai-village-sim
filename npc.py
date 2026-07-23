"""
npc.py — 개별 NPC 에이전트.

decide_action()과 speak()가 이 프로젝트의 "에이전틱" 파트: NPC가 스스로
관련 기억을 찾아보고(RAG), 그걸 근거로 다음 행동/대사를 계획한다.
perceive()로 들어온 모든 사건은 memory에 쌓여서 나중 턴의 판단 근거가 된다.
"""

from memory import MemoryStream
from llm import call_llm, parse_json_safely


class NPC:
    def __init__(self, name: str, personality: str, location: str):
        self.name = name
        self.personality = personality
        self.location = location
        self.memory = MemoryStream()

    def perceive(self, event: str):
        """마을에서 일어난 사건을 기억에 저장 (시뮬레이션 이벤트 -> 기억)."""
        self.memory.add(event, kind="observation")

    def decide_action(self, current_time: str, nearby_npcs: list[str]) -> dict:
        """이번 턴에 뭘 할지 스스로 계획. 관련 기억을 RAG로 검색해 근거로 사용."""
        query = f"{current_time}, 장소: {self.location}, 주변 인물: {', '.join(nearby_npcs) or '없음'}"
        memories = self.memory.retrieve(query, k=5)
        memory_text = "\n".join(f"- {m.content}" for m in memories) or "(관련 기억 없음)"

        system_prompt = (
            f"너는 마을 주민 '{self.name}'이다. 성격: {self.personality}. "
            "반드시 JSON 한 덩어리로만 답하고 다른 말은 하지 마라."
        )
        user_prompt = f"""현재 시각: {current_time}
현재 위치: {self.location}
관련 기억:
{memory_text}
주변 인물: {', '.join(nearby_npcs) or '없음'}

이번 턴에 할 행동을 정해라. 다음 JSON 형식으로만 답해:
{{"action": "행동을 10자 내외로 요약", "move_to": "이동할 장소 (그대로면 현재 위치와 동일하게)"}}"""

        raw = call_llm(system_prompt, user_prompt, max_tokens=150)
        result = parse_json_safely(raw)
        result.setdefault("action", "가만히 있는다")
        result.setdefault("move_to", self.location)
        return result

    def speak(self, transcript: list[str], other_names: list[str]) -> str:
        """같은 장소에 있는 다른 NPC와의 대화 중 한 마디를 생성."""
        query = f"{', '.join(other_names)}와의 대화. 지금까지: {' / '.join(transcript[-4:])}"
        memories = self.memory.retrieve(query, k=3)
        memory_text = "\n".join(f"- {m.content}" for m in memories) or "(관련 기억 없음)"

        system_prompt = (
            f"너는 마을 주민 '{self.name}'이다. 성격: {self.personality}. "
            "자연스러운 대사 한 줄만 출력해라. 따옴표나 이름 접두사 없이 대사 내용만."
        )
        user_prompt = f"""대화 상대: {', '.join(other_names)}
관련 기억:
{memory_text}
지금까지의 대화:
{chr(10).join(transcript) if transcript else "(대화 시작)"}

다음 대사 한 줄만 말해줘 (1~2문장)."""

        line = call_llm(system_prompt, user_prompt, max_tokens=100)
        return line.strip().strip('"')
