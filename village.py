"""
village.py — 이 프로젝트의 "하네스" + "시뮬레이션" 파트.

Village.run_tick()이 매 턴마다 모든 NPC를 순회하며
perceive -> (같은 장소면 대화) -> decide_action 순서로 실행하는 스케줄러(하네스)다.
scripted_events()는 마을에 주입되는 이벤트로, "시뮬레이션" 파트를 담당한다.
여기에 원하는 이벤트를 자유롭게 추가하면 NPC들의 반응이 달라지는 걸 바로 확인할 수 있다.

LOCATION_COORDS와 get_state()는 웹 프론트엔드(app.py)가 지도 위에 NPC를
움직이는 그림으로 그리기 위해 추가된 부분. CLI(main.py)만 쓸 거면 몰라도 됨.
"""

import time

from npc import NPC

# 지도 위 위치(%, %) — app.py의 index.html이 이 좌표를 그대로 받아서 그린다.
LOCATION_COORDS = {
    "카페": {"x": 20, "y": 25},
    "도서관": {"x": 78, "y": 25},
    "광장": {"x": 49, "y": 55},
    "공원": {"x": 49, "y": 85},
}


class Village:
    def __init__(self, npcs: list[NPC], tick_delay: float = 1.0):
        self.npcs = npcs
        self.tick_count = 0
        self.locations: dict[str, list[str]] = {}
        self.tick_delay = tick_delay
        self.log: list[dict] = []

    def scripted_events(self) -> dict[int, str]:
        return {
            3: "마을 전체에 정전이 발생했다.",
            6: "낯선 여행자가 마을 광장에 나타났다.",
        }

    def _emit(self, entry_type: str, text: str, npc_name: str | None = None):
        self.log.append({
            "type": entry_type,
            "tick": self.tick_count,
            "npc": npc_name,
            "text": text,
        })

    def _update_locations(self):
        self.locations = {}
        for npc in self.npcs:
            self.locations.setdefault(npc.location, []).append(npc.name)

    def _run_conversation(self, location: str, names: list[str], turns: int = 3):
        participants = [n for n in self.npcs if n.name in names]
        print(f"\n  📍 {location}에서 {', '.join(names)} 마주침")
        self._emit("meet", f"{location}에서 {', '.join(names)} 마주침")

        transcript: list[str] = []
        for i in range(turns):
            speaker = participants[i % len(participants)]
            others = [p.name for p in participants if p is not speaker]
            line = speaker.speak(transcript, others)
            print(f"     💬 {speaker.name}: {line}")
            self._emit("dialogue", line, npc_name=speaker.name)
            transcript.append(f"{speaker.name}: {line}")

        summary = " / ".join(transcript)
        for p in participants:
            p.memory.add(f"{location}에서 {', '.join(o for o in names if o != p.name)}와 대화: {summary}",
                          importance=6, kind="dialogue")

    def run_tick(self) -> dict:
        self.tick_count += 1
        current_time = f"Day1 {8 + self.tick_count}:00"
        print(f"\n===== {current_time} (tick {self.tick_count}) =====")

        event = self.scripted_events().get(self.tick_count)
        if event:
            print(f"⚡ [이벤트] {event}")
            self._emit("event", event)
            for npc in self.npcs:
                npc.perceive(event)

        self._update_locations()

        handled: set[str] = set()
        for location, names in self.locations.items():
            if len(names) >= 2:
                self._run_conversation(location, names)
                handled.update(names)

        for npc in self.npcs:
            if npc.name in handled:
                continue
            nearby = [n for n in self.locations.get(npc.location, []) if n != npc.name]
            action = npc.decide_action(current_time, nearby)
            print(f"  🧍 {npc.name} @ {npc.location}: {action['action']}")
            self._emit("action", action["action"], npc_name=npc.name)
            npc.memory.add(f"[{current_time}] {action['action']}", importance=3)

            move_to = action.get("move_to")
            if move_to and move_to != npc.location and move_to in LOCATION_COORDS:
                print(f"     🚶 {npc.name} -> {move_to}")
                self._emit("move", f"{npc.name} -> {move_to}", npc_name=npc.name)
                npc.location = move_to

        if self.tick_delay:
            time.sleep(self.tick_delay)

        return self.get_state()

    def get_state(self, log_limit: int = 30) -> dict:
        return {
            "tick": self.tick_count,
            "time": f"Day1 {8 + self.tick_count}:00" if self.tick_count else "시작 전",
            "locations": LOCATION_COORDS,
            "npcs": [
                {"name": n.name, "location": n.location, "personality": n.personality}
                for n in self.npcs
            ],
            "log": self.log[-log_limit:],
        }
