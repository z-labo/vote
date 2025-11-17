import os
import json
from datetime import datetime, timezone

from flask import Flask, request, jsonify
import dropbox

app = Flask(__name__)

# 환경변수에서 Dropbox 토큰 읽기
DROPBOX_TOKEN = os.environ.get("DROPBOX_TOKEN")
DROPBOX_BASE_FOLDER = "/vote_results"  # Dropbox 안의 저장 폴더 (미리 하나 만들어 두는 것을 권장)

if not DROPBOX_TOKEN:
  raise RuntimeError("환경변수 DROPBOX_TOKEN 이 설정되어 있지 않습니다.")

# Dropbox 클라이언트 (필요할 때마다 새로 만들어도 되고, 전역으로 써도 됨)
def get_dbx():
  return dropbox.Dropbox(DROPBOX_TOKEN)


@app.route("/submit_vote", methods=["POST"])
def submit_vote():
  # 1) JSON 받아오기
  try:
    data = request.get_json(force=True)
  except Exception:
    return jsonify({"ok": False, "error": "invalid_json"}), 400

  # 2) 최소한의 검증
  judge_id = data.get("judgeId")
  results = data.get("results")

  if not judge_id or not isinstance(results, list):
    return jsonify({"ok": False, "error": "bad_payload"}), 400

  # 3) 파일 이름/경로 만들기
  #    예: J1_2025-11-17T09-00-00Z.json
  ts = data.get("timestamp")
  if ts is None:
    ts = datetime.now(timezone.utc).isoformat()

  safe_ts = ts.replace(":", "-")  # Windows/Dropbox 경로에 안전하게
  filename = f"{judge_id}_{safe_ts}.json"

  dropbox_path = f"{DROPBOX_BASE_FOLDER}/{filename}"

  # 4) Dropbox에 업로드
  dbx = get_dbx()
  try:
    # JSON 문자열로 인코딩 (UTF-8)
    content = json.dumps(data, ensure_ascii=False, indent=2)
    dbx.files_upload(
      content.encode("utf-8"),
      dropbox_path,
      mode=dropbox.files.WriteMode.add  # 같은 이름 있으면 에러, 덮어쓰려면 .overwrite
    )
  except Exception as e:
    # 로그용으로 출력(호스팅 서비스의 로그에서 확인)
    print("Dropbox upload error:", repr(e))
    return jsonify({"ok": False, "error": "dropbox_upload_failed"}), 500

  # 5) 클라이언트에 성공 응답
  return jsonify({"ok": True, "path": dropbox_path})
