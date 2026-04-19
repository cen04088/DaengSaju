import os, django, sys
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from saju.models import DailyLuckArchetype, ArchetypeSaju, DailyWalkingLuck, DailyElementLuck

def get_samples():
    print("--- DailyLuckArchetype Sample ---")
    arch = DailyLuckArchetype.objects.filter(version='A').first()
    if arch:
        print(f"[{len(arch.message)} chars] Message:\n{arch.message[:200]}...")
        print("-" * 20)
        
    print("\n--- DailyWalkingLuck Sample (오늘의 산책 컨디션) ---")
    luck = DailyWalkingLuck.objects.all().order_by('-date').first()
    if luck:
        print(f"[{len(luck.message)} chars] Message:\n{luck.message[:200]}...")
        print("-" * 20)

    print("\n--- ArchetypeSaju Sample ---")
    arch = ArchetypeSaju.objects.first()
    if arch:
        print(f"[{len(arch.vitality_analysis)} chars] Vitality:\n{arch.vitality_analysis[:200]}...")
        print("-" * 20)

if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    get_samples()
