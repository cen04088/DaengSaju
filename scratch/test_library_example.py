from sajupy import SajuCalculator
import sys

# Set encoding for output
sys.stdout.reconfigure(encoding='utf-8')

def test_calculator(y, m, d, h=14, mi=30):
    calc = SajuCalculator()
    res = calc.calculate_saju(y, m, d, h, mi)
    print(f"\n--- SajuCalculator Result for {y}-{m}-{d} {h}:{mi} ---")
    print(f"Year: {res.get('year_pillar')}")
    print(f"Month: {res.get('month_pillar')}")
    print(f"Day: {res.get('day_pillar')}")
    print(f"Day Stem: {res.get('day_stem')}")

# library's example
test_calculator(1990, 10, 10, 14, 30)
