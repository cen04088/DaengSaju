from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "db.sqlite3"
BACKUP_DIR = ROOT / "scratch" / "backups"


TEXT_COLUMNS = {
    "saju_archetypesaju": [
        "personality_summary",
        "vitality_analysis",
        "social_analysis",
        "treat_luck",
        "care_tips",
    ],
    "saju_compatibilityarchetype": ["title", "description", "advice"],
    "saju_dailyluckarchetype": ["message", "lucky_color", "lucky_direction"],
}


GLOBAL_REPLACEMENTS = [
    ("주종 관계", "든든한 팀워크"),
    ("복종의 신호", "신뢰의 신호"),
    ("'복종'", "'신뢰'"),
    (" 전용 비서이자 보디가드", " 든든한 매니저이자 수호자"),
    ("전용 비서이자 보디가드", "든든한 매니저이자 수호자"),
    ("보디가드", "수호자"),
    ("뿜뿜", "가득"),
    ("폭풍 칭찬", "아낌없는 칭찬"),
    ("한 성깔(?)", "고집 한 번"),
    ("캐미", "케미"),
    ("cuddling", "포근한 스킨십"),
]


DAILY_MESSAGE_REPLACEMENTS = [
    ("playful한", "장난기 가득한"),
    ("규율과 통제", "차분한 집중과 질서"),
    ("사랑스러운 [강아지이름]님", "사랑스러운 [강아지이름]"),
    ("오늘 당신에게 작용하는 기운은 바로", "오늘 [강아지이름]에게 작용하는 기운은 바로"),
    ("당신에게 특별한 기운이 감도는 날입니다.", "[강아지이름]에게 특별한 기운이 감도는 날입니다."),
]


SHORT_LABEL_REPLACEMENTS = {
    "베이지 (Beige)": "베이지",
    "남서쪽 (South-West)": "남서쪽",
    "남색 (혹은 검은색)": "남색",
    "황토색 (earthy yellow)": "황토색",
    "하얀색 (또는 은색)": "하얀색",
    "딥 블루 (차분함과 집중력)": "딥 블루",
    "북쪽 (안정과 균형)": "북쪽",
    "노란색 (Yellow)": "노란색",
    "초록색 (Green)": "초록색",
    "동쪽 (East)": "동쪽",
    "골드 (Gold)": "골드",
    "서쪽 (West)": "서쪽",
    "서쪽, 북서쪽": "서쪽",
    "남서쪽 (South-West), 서쪽 (West)": "남서쪽",
    "남서쪽 (South-West)": "남서쪽",
}


def backup_database() -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"db_before_soften_{timestamp}.sqlite3"
    shutil.copy2(DB_PATH, backup_path)
    return backup_path


def apply_replacements(text: str, replacements: list[tuple[str, str]]) -> str:
    result = text
    for old, new in replacements:
        result = result.replace(old, new)
    return result


def normalize_daily_label(value: str) -> str:
    normalized = value.strip()
    normalized = SHORT_LABEL_REPLACEMENTS.get(normalized, normalized)
    if " (" in normalized and normalized.endswith(")"):
        normalized = normalized.split(" (", 1)[0].strip()
    if "," in normalized:
        normalized = normalized.split(",", 1)[0].strip()
    return normalized


def soften_text(table: str, column: str, value: str) -> str:
    softened = apply_replacements(value, GLOBAL_REPLACEMENTS)

    if table == "saju_dailyluckarchetype" and column == "message":
        softened = apply_replacements(softened, DAILY_MESSAGE_REPLACEMENTS)

    if table == "saju_dailyluckarchetype" and column in {"lucky_color", "lucky_direction"}:
        softened = normalize_daily_label(softened)

    if table == "saju_dailyluckarchetype" and column == "message":
        softened = softened.replace("[강아지이름]님", "[강아지이름]")

    return softened


def main() -> None:
    backup_path = backup_database()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    updated_cells = 0
    updated_rows = 0

    for table, columns in TEXT_COLUMNS.items():
        cur.execute(f"SELECT rowid, {', '.join(columns)} FROM {table}")
        rows = cur.fetchall()

        for row in rows:
            rowid = row[0]
            original_values = dict(zip(columns, row[1:]))
            changed = {}

            for column, value in original_values.items():
                if not isinstance(value, str) or not value:
                    continue
                softened = soften_text(table, column, value)
                if softened != value:
                    changed[column] = softened

            if changed:
                assignments = ", ".join(f"{column} = ?" for column in changed)
                params = list(changed.values()) + [rowid]
                cur.execute(f"UPDATE {table} SET {assignments} WHERE rowid = ?", params)
                updated_rows += 1
                updated_cells += len(changed)

    conn.commit()
    conn.close()

    print(f"backup={backup_path}")
    print(f"updated_rows={updated_rows}")
    print(f"updated_cells={updated_cells}")


if __name__ == "__main__":
    main()
