import sqlite3
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "db.sqlite3"
REPORT_PATH = ROOT / "scratch" / "template_audit_report.md"


TABLE_CONFIG = {
    "saju_archetypesaju": {
        "label": "평생 사주",
        "id_fields": ["primary_element", "relationship_type", "version"],
        "text_fields": [
            "personality_summary",
            "vitality_analysis",
            "social_analysis",
            "treat_luck",
            "care_tips",
        ],
    },
    "saju_compatibilityarchetype": {
        "label": "댕궁합",
        "id_fields": ["dog_element", "relationship_type", "version"],
        "text_fields": ["title", "description", "advice"],
    },
    "saju_dailyluckarchetype": {
        "label": "오늘 운세",
        "id_fields": ["dog_element", "relationship_type", "version"],
        "text_fields": ["message", "lucky_color", "lucky_direction"],
    },
}


CHECKS = [
    {
        "name": "톤 과장/유치 표현",
        "severity": "high",
        "patterns": ["주종 관계", "복종", "전용 비서", "보디가드", "한 성깔", "뿜뿜", "폭풍 칭찬"],
        "reason": "인앱 배포용 문구로 보기엔 유치하거나 불편하게 느껴질 수 있는 표현",
    },
    {
        "name": "영어 혼용",
        "severity": "medium",
        "patterns": ["playful", "Beige", "South-West", "North", "West"],
        "reason": "한국어 문맥 안에서 갑자기 영어가 섞여 톤이 흔들림",
    },
    {
        "name": "플레이스홀더 조사 불안정",
        "severity": "high",
        "patterns": ["[강아지이름]와", "[강아지이름]는", "[보호자이름]와", "[보호자이름]는"],
        "reason": "런타임 치환 이전 원문 기준으로 이미 어색하며 후처리에 과하게 의존함",
    },
    {
        "name": "불필요한 공백/문장부호",
        "severity": "low",
        "patterns": ["  ", " ?\n", " .", " !", " ?"],
        "reason": "문장 리듬이 끊기거나 편집 흔적처럼 보일 수 있음",
    },
]


def fetch_rows(cur, table_name, id_fields, text_fields):
    fields = ", ".join(id_fields + text_fields)
    cur.execute(f"SELECT {fields} FROM {table_name}")
    rows = []
    for row in cur.fetchall():
        data = dict(zip(id_fields + text_fields, row))
        rows.append(data)
    return rows


def normalize_text(value):
    if not isinstance(value, str):
        return ""
    return value.replace("\r\n", "\n").replace("\r", "\n")


def detect_long_paragraphs(text):
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    return [p for p in paragraphs if len(p) >= 280]


def detect_short_fragments(text):
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    return [p for p in paragraphs if len(p) <= 12]


def detect_checks(text):
    hits = []
    for check in CHECKS:
        matched = [pattern for pattern in check["patterns"] if pattern in text]
        if matched:
            hits.append((check, matched))
    return hits


def make_row_key(row, id_fields):
    return "/".join(str(row[field]) for field in id_fields)


def build_report(results, totals):
    lines = []
    lines.append("# 템플릿 품질 점검 리포트")
    lines.append("")
    lines.append("## 점검 기준")
    lines.append("- 읽기 흐름: 한 문단이 지나치게 길지 않은지")
    lines.append("- 문맥 자연스러움: 표현이 과장되거나 불편하지 않은지")
    lines.append("- 톤 일관성: 서비스 전반의 말투와 맞는지")
    lines.append("- 치환 안정성: 플레이스홀더와 조사 결합이 원문부터 자연스러운지")
    lines.append("- 표기 일관성: 영어 혼용, 불필요한 공백, 문장부호 흔들림이 없는지")
    lines.append("")
    lines.append("## 테이블 수량")
    for label, count in totals:
        lines.append(f"- {label}: {count}개")
    lines.append("")

    for section in results:
        lines.append(f"## {section['label']}")
        lines.append(f"- 점검 대상: {section['count']}개")
        lines.append(f"- 문제 감지 건수: {section['issue_count']}건")
        lines.append("")

        if not section["issues"]:
            lines.append("- 눈에 띄는 문제 없음")
            lines.append("")
            continue

        grouped = defaultdict(list)
        for issue in section["issues"]:
            grouped[issue["category"]].append(issue)

        for category, issues in grouped.items():
            lines.append(f"### {category}")
            lines.append(f"- 감지 건수: {len(issues)}")
            lines.append(f"- 판단: {issues[0]['reason']}")
            for issue in issues[:8]:
                lines.append(
                    f"- `{issue['key']}` / `{issue['field']}`: {issue['excerpt']}"
                )
            if len(issues) > 8:
                lines.append(f"- 외 {len(issues) - 8}건")
            lines.append("")

    lines.append("## 정리")
    lines.append("- 평생 사주 템플릿은 조사와 말맛이 어색한 문장이 섞여 있고, 버전별 길이 편차가 큽니다.")
    lines.append("- 댕궁합 템플릿은 과장된 관계 묘사와 유치한 비유가 일부 포함됩니다.")
    lines.append("- 오늘 운세 템플릿은 비교적 안정적이지만 영어 혼용과 색/방향 표기 불일치가 있습니다.")
    lines.append("")
    return "\n".join(lines) + "\n"


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    results = []
    totals = []

    for table_name, config in TABLE_CONFIG.items():
        rows = fetch_rows(cur, table_name, config["id_fields"], config["text_fields"])
        totals.append((config["label"], len(rows)))
        issues = []

        for row in rows:
            key = make_row_key(row, config["id_fields"])
            for field in config["text_fields"]:
                text = normalize_text(row.get(field, ""))
                if not text:
                    continue

                for paragraph in detect_long_paragraphs(text):
                    issues.append(
                        {
                            "category": "긴 문단",
                            "reason": "한 문단이 너무 길어 카드 UI에서 훑어 읽기 어렵습니다.",
                            "key": key,
                            "field": field,
                            "excerpt": paragraph[:140] + ("..." if len(paragraph) > 140 else ""),
                        }
                    )

                for fragment in detect_short_fragments(text):
                    issues.append(
                        {
                            "category": "짧게 끊긴 문장",
                            "reason": "짧게 끊긴 문장이 문맥 흐름을 어색하게 만듭니다.",
                            "key": key,
                            "field": field,
                            "excerpt": fragment,
                        }
                    )

                for check, matched in detect_checks(text):
                    issues.append(
                        {
                            "category": check["name"],
                            "reason": check["reason"],
                            "key": key,
                            "field": field,
                            "excerpt": f"{', '.join(matched)} / {text[:120]}...",
                        }
                    )

        results.append(
            {
                "label": config["label"],
                "count": len(rows),
                "issue_count": len(issues),
                "issues": issues,
            }
        )

    REPORT_PATH.write_text(build_report(results, totals), encoding="utf-8")
    print(REPORT_PATH)


if __name__ == "__main__":
    main()
