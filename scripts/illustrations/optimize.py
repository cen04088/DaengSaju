"""새 일러스트 원본(PNG)을 앱 표시용 WebP로 바꿔 frontend/public/assets/ 에 둔다.

사용법:
    python scripts/illustrations/optimize.py <dog|zodiac|state|talisman> 원본.png [원본2.png ...] [--crop]

- 종횡비가 규격과 다르면 늘리지 않고 멈춘다. --crop 을 주면 가운데를 잘라 맞춘다.
- talisman 은 표시용 WebP(440×880)와 함께 '부적 저장하기'용 PNG(887×1774)도 만든다.
"""
import argparse
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT_DIR = os.path.join(ROOT, 'frontend', 'public', 'assets')

SPECS = {
    'dog': {'display': (480, 480), 'quality': 82},
    'zodiac': {'display': (480, 480), 'quality': 82},
    'state': {'display': (480, 480), 'quality': 82},
    'talisman': {'display': (440, 880), 'quality': 80, 'original': (887, 1774)},
}


def fit(image, size, crop):
    """size 비율로 맞춘 뒤 리사이즈. 비율이 다르면 crop=True일 때만 가운데를 자른다."""
    target_ratio = size[0] / size[1]
    ratio = image.width / image.height
    if abs(ratio - target_ratio) > 0.01:
        if not crop:
            raise ValueError(f'종횡비 {image.width}x{image.height} 가 규격 {size[0]}x{size[1]} 과 다릅니다 (--crop 으로 가운데 자르기)')
        if ratio > target_ratio:
            new_w = round(image.height * target_ratio)
            left = (image.width - new_w) // 2
            image = image.crop((left, 0, left + new_w, image.height))
        else:
            new_h = round(image.width / target_ratio)
            top = (image.height - new_h) // 2
            image = image.crop((0, top, image.width, top + new_h))
    return image.resize(size, Image.LANCZOS)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('kind', choices=sorted(SPECS))
    parser.add_argument('sources', nargs='+')
    parser.add_argument('--crop', action='store_true', help='종횡비가 다르면 가운데를 잘라 맞춤')
    parser.add_argument('--out', default=OUT_DIR, help='결과 폴더 (기본: frontend/public/assets)')
    args = parser.parse_args()
    spec = SPECS[args.kind]

    failed = False
    for src in args.sources:
        name = os.path.splitext(os.path.basename(src))[0]
        try:
            image = Image.open(src).convert('RGB')
            display = fit(image, spec['display'], args.crop)
            webp_path = os.path.join(args.out, f'{name}.webp')
            display.save(webp_path, 'WEBP', quality=spec['quality'], method=6)
            print(f'{webp_path}  {display.width}x{display.height}  {os.path.getsize(webp_path) // 1024}KB')
            if 'original' in spec:
                # 기존 부적 원본처럼 256색 팔레트 PNG로 저장(용량 절반 수준)
                original = fit(image, spec['original'], args.crop).quantize(colors=256, method=Image.Quantize.MEDIANCUT)
                png_path = os.path.join(args.out, f'{name}.png')
                original.save(png_path, 'PNG', optimize=True)
                print(f'{png_path}  {original.width}x{original.height}  {os.path.getsize(png_path) // 1024}KB')
        except (OSError, ValueError) as error:
            failed = True
            print(f'{src}: {error}', file=sys.stderr)
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
