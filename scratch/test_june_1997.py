from sajupy import SajuCalculator
import sys

# Set encoding for output
sys.stdout.reconfigure(encoding='utf-8')

def test_calculator(y, m, d):
    calc = SajuCalculator()
    res = calc.calculate_saju(y, m, d, 12, 0)
    print(f"Result for {y}-{m:02d}-{d:02d}: {res.get('day_pillar')} ({res.get('day_stem')})")

test_calculator(1997, 6, 28)
test_calculator(1997, 6, 29)
test_calculator(1997, 6, 30)
