"""
main.py — 실행 진입점. 캐릭터/성격을 여기서 자유롭게 바꾸는 게
커스터마이징의 8할이다. 이름, 성격, 시작 위치만 바꿔도 완전히 다른 마을이 됨.
"""

from village import Village
from npc import NPC


def build_village() -> Village:
    npcs = [
        NPC("수아", "호기심 많고 사교적인 카페 사장. 새로운 사람을 만나는 걸 좋아함", "카페"),
        NPC("민준", "내성적인 대학원생. 혼자 연구하는 걸 선호하지만 은근히 외로움을 느낌", "도서관"),
        NPC("지호", "마을 이장. 책임감이 강하고 사람들을 챙기는 걸 좋아함", "광장"),
    ]
    return Village(npcs, tick_delay=1.0)


def main(num_ticks: int = 8):
    print("=== AI 마을 시뮬레이션 시작 ===")
    village = build_village()
    for _ in range(num_ticks):
        village.run_tick()
    print("\n=== 시뮬레이션 종료 ===")


if __name__ == "__main__":
    main()
