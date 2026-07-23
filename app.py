"""
app.py — 웹 프론트엔드용 Flask 서버.

실시간으로 지도 위에서 NPC가 움직이는 걸 보여주기 위해 Streamlit 대신
일반 Flask + HTML/CSS/JS로 구성했다. Streamlit은 매 상호작용마다 화면
전체를 다시 그리기 때문에 부드러운 이동 애니메이션을 만들기 어렵지만,
여기서는 브라우저 쪽 JS가 NPC 마커의 CSS 좌표만 바꾸고 나머지 DOM은
그대로 유지하기 때문에 CSS transition으로 실제 "움직이는" 느낌을 낼 수 있다.

동작 방식:
  1. GET  /            -> 지도 페이지(HTML) 서빙
  2. GET  /api/state   -> 현재 상태(스냅샷) JSON
  3. POST /api/tick    -> 한 턴 진행(Gemini 호출 발생) 후 최신 상태 JSON 반환
  4. POST /api/reset   -> 시뮬레이션 초기화

프론트엔드(static/app.js)가 /api/tick을 주기적으로 호출(폴링)하면서
NPC 좌표가 바뀔 때마다 CSS transition으로 부드럽게 이동시킨다.
"""

from flask import Flask, jsonify, render_template

from village import Village
from npc import NPC

app = Flask(__name__)

village: Village | None = None


def build_village() -> Village:
    npcs = [
        NPC("수아", "호기심 많고 사교적인 카페 사장. 새로운 사람을 만나는 걸 좋아함", "카페"),
        NPC("민준", "내성적인 대학원생. 혼자 연구하는 걸 선호하지만 은근히 외로움을 느낌", "도서관"),
        NPC("지호", "마을 이장. 책임감이 강하고 사람들을 챙기는 걸 좋아함", "광장"),
    ]
    return Village(npcs, tick_delay=0)  # 웹에서는 서버 쪽 sleep 대신 프론트 애니메이션으로 템포 조절


def get_village() -> Village:
    global village
    if village is None:
        village = build_village()
    return village


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/state", methods=["GET"])
def api_state():
    return jsonify(get_village().get_state())


@app.route("/api/tick", methods=["POST"])
def api_tick():
    v = get_village()
    try:
        state = v.run_tick()
        return jsonify(state)
    except RuntimeError as e:
        # GEMINI_API_KEY 누락 등 설정 에러
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"틱 진행 중 오류: {e}"}), 500


@app.route("/api/reset", methods=["POST"])
def api_reset():
    global village
    village = build_village()
    return jsonify(village.get_state())


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
