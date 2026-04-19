from sajupy import SajuCalculator
import sys

# Set encoding for output
sys.stdout.reconfigure(encoding='utf-8')

def test_calculator(y, m, d):
    calc = SajuCalculator()
    # Testing with explicit parameters
    res = calc.calculate_saju(y, m, d, 12, 0, city="Seoul")
    print(f"\n--- SajuCalculator Result for {y}-{m}-{d} ---")
    print(f"Year: {res.get('year_pillar')}")
    print(f"Month: {res.get('month_pillar')}")
    print(f"Day: {res.get('day_pillar')}")
    print(f"Day Stem: {res.get('day_stem')}")

test_calculator(1997, 6, 29)
