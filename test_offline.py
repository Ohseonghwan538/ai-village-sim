"""
test_offline.py — API 키 없이(=비용/시간 소모 없이) 하네스 로직만 빠르게 검증하는 스모크 테스트.

llm.call_llm을 가짜 응답으로 바꿔치기해서 스케줄러/대화/이벤트 주입 로직에
버그가 없는지만 확인한다. 실제 대사 품질은 확인할 수 없으니, 로직을 고친
직후 "일단 안 터지는지"만 빠르게 볼 때 쓰면 된다. 진짜 데모는 반드시
`python main.py`로 (API 키 넣고) 돌려볼 것.
"""

import json
import random

import llm

ACTIONS = ["커피를 내린다", "책을 읽는다", "마을을 순찰한다", "산책을 한다", "일지를 쓴다"]
LOCATIONS = ["카페", "도서관", "광장", "공원"]
LINES = ["요즘 마을에 별일 없어?", "그러게, 오늘따라 조용하네.", "다음에 또 얘기하자!"]


def fake_call_llm(system_prompt: str, user_prompt: str, max_tokens: int = 250) -> str:
    if "다음 대사 한 줄만" in user_prompt:
        return random.choice(LINES)
    return json.dumps(
        {"action": random.choice(ACTIONS), "move_to": random.choice(LOCATIONS)},
        ensure_ascii=False,
    )


def main():
    llm.call_llm = fake_call_llm  # 실제 API 호출을 가짜 함수로 교체

    from main import build_village

    village = build_village()
    village.tick_delay = 0  # 테스트는 딜레이 없이 빠르게

    for _ in range(5):
        village.run_tick()

    print("\n[OK] 5틱 정상 실행됨 (오프라인 목업). NPC별 누적 메모리 수:")
    for npc in village.npcs:
        print(f"  {npc.name}: {len(npc.memory.memories)}개")


if __name__ == "__main__":
    main()
