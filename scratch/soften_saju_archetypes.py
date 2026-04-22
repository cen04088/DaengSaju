from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "db.sqlite3"
BACKUP_DIR = ROOT / "scratch" / "backups"
TABLE = "saju_archetypesaju"
COLUMNS = [
    "personality_summary",
    "vitality_analysis",
    "social_analysis",
    "treat_luck",
    "care_tips",
]


REPLACEMENTS = [
    ("규율 대장", "질서감 있는 리더"),
    ("개린이", "댕댕이"),
    ("핵인싸", "인싸"),
    ("우악스럽게", "급하게"),
    ("'내놔라!' 시위", "'주세요!' 하는 눈빛"),
    ("'주세요!' 하는 눈빛를 하다가도", "'주세요!' 하는 눈빛을 보내다가도"),
    ("적정량을 지켜주는 센스!\n\n잊지 마세요.", "적정량을 지켜주는 보호자님의 센스가 특히 중요해요."),
    ("사회성도 '자신만의 방식'으로 발휘하는 아이랍니다.", "사회성도 자기만의 템포로 보여주는 아이랍니다."),
    ("'내 영역을 침범하지 마라'는 무언의 신호", "'조금 천천히 다가와 줘'라는 무언의 신호"),
    ("사회생활 만점 강아지", "사회성이 안정적인 강아지"),
]


def backup_database() -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"db_before_saju_soften_{timestamp}.sqlite3"
    shutil.copy2(DB_PATH, backup_path)
    return backup_path


def clean_text(text: str) -> str:
    result = text
    for old, new in REPLACEMENTS:
        result = result.replace(old, new)

    result = result.replace("  ", " ")
    result = result.replace(" .", ".")
    result = result.replace(" !", "!")
    result = result.replace(" ?", "?")
    result = result.replace("죠 .", "죠.")
    result = result.replace("깊어요 .", "깊어요.")
    result = result.replace("예요 .", "예요.")
    result = result.replace("깊어요  ", "깊어요 ")
    result = result.replace("기운에는 매우 예민하게 반응하여", "기운에는 예민하게 반응하여")
    return result


def main() -> None:
    backup_path = backup_database()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    updated_rows = 0
    updated_cells = 0

    cur.execute(f"SELECT rowid, {', '.join(COLUMNS)} FROM {TABLE}")
    for row in cur.fetchall():
        rowid = row[0]
        changed = {}
        for column, value in zip(COLUMNS, row[1:]):
            if not isinstance(value, str) or not value:
                continue
            cleaned = clean_text(value)
            if cleaned != value:
                changed[column] = cleaned

        if changed:
            assignments = ", ".join(f"{column} = ?" for column in changed)
            params = list(changed.values()) + [rowid]
            cur.execute(f"UPDATE {TABLE} SET {assignments} WHERE rowid = ?", params)
            updated_rows += 1
            updated_cells += len(changed)

    conn.commit()
    conn.close()

    print(f"backup={backup_path}")
    print(f"updated_rows={updated_rows}")
    print(f"updated_cells={updated_cells}")


if __name__ == "__main__":
    main()
