"""운세 문구의 문장 끝 어미를 해요체로 맞춥니다.

사전 생성 문구에 합니다체(~입니다·~습니다·~랍니다·~답니다)가 해요체와 섞여 있어
어미만 해요체(~이에요·~어요·~해요)로 바꿉니다. 이미 해요체인 문장은 그대로 두므로
같은 글에 여러 번 적용해도 결과가 같습니다.
"""
import re

_BASE = 0xAC00
# 중성 번호
_A, _AE, _YA, _YAE, _EO, _E, _YEO, _YE, _O, _WA, _WAE, _OE = range(12)
_U, _WO, _WI, _EU, _UI, _I = 13, 14, 16, 18, 19, 20
# 종성 번호
_NIEUN, _RIEUL, _BIEUP, _SSANGSIOT = 4, 8, 17, 20

# ㅂ 불규칙 용언 어간 (가깝다 → 가까워요)
_BIEUP_IRREGULAR = (
    '가깝', '사랑스럽', '자연스럽', '아름답', '귀엽', '즐겁', '반갑', '고맙', '어렵', '쉽', '무섭',
    '부드럽', '새롭', '놀랍', '아쉽', '정답', '그립', '외롭', '날카롭', '뜨겁', '차갑', '가볍',
    '무겁', '두렵', '부럽', '덥', '춥', '향기롭', '여유롭', '평화롭', '자유롭', '해롭', '이롭',
)
# '르'로 끝나지만 르 불규칙이 아닌 어간 (따르다 → 따라요)
_EU_DROP_REU = ('따르', '치르', '들르', '우러르')
# ㄹ 받침이 'ㄴ' 앞에서 떨어진 동사 어간 끝 (달려든답니다 → 달려들다, 만든답니다 → 만들다)
_RIEUL_DROPPED = {'드': '들'}
# '이'로 끝나는 명사 (댕댕이랍니다 → 댕댕이예요). 이 밖의 'X이랍니다'는 X + 이에요
_I_NOUN_SUFFIXES = ('아이', '댕이', '둥이', '덩이', '린이', '멍이', '쟁이', '돌이', '순이')
# '-이다' 동사 어간에서 '이'를 뺀 어절 (보입니다 → 보여요). 명사+입니다(정보입니다)와 구분하려고 어절 전체로 비교
_I_VERB_BASES = ('보', '돋보', '엿보', '먹', '높', '붙', '쌓')

_TOKEN = re.compile(r'(\S+?니다)(?=[\s.!?~,:;"\'”’)…]|$)')


def _is_hangul(ch):
    return _BASE <= ord(ch) <= 0xD7A3


def _split(ch):
    code = ord(ch) - _BASE
    return code // 588, (code % 588) // 28, code % 28


def _join(cho, jung, jong=0):
    return chr(_BASE + cho * 588 + jung * 28 + jong)


def conjugate(stem):
    """용언 어간에 해요체 '-아요/-어요'를 붙입니다. (좋 → 좋아요, 되 → 돼요, 모르 → 몰라요)"""
    last = stem[-1]
    if not _is_hangul(last):
        return None
    if last == '하':
        return stem[:-1] + '해요'
    if stem.endswith(('돕', '곱')):  # ㅂ 불규칙 중 '-와요' (도와요, 고와요)
        cho, jung, _ = _split(last)
        return stem[:-1] + _join(cho, jung) + '와요'
    for irregular in _BIEUP_IRREGULAR:
        if stem.endswith(irregular):
            cho, jung, _ = _split(last)
            return stem[:-1] + _join(cho, jung) + '워요'
    cho, jung, jong = _split(last)
    if jong:
        if jong == _SSANGSIOT:  # 있·었·겠 → 있어요·었어요·겠어요
            return stem + '어요'
        return stem + ('아요' if jung in (_A, _O) else '어요')
    if jung in (_A, _AE, _YA, _YAE, _EO, _E, _YEO, _YE):
        return stem + '요'
    if jung == _O:
        return stem[:-1] + _join(cho, _WA) + '요'
    if jung == _U:
        return stem[:-1] + _join(cho, _WO) + '요'
    if jung == _OE:
        return stem[:-1] + _join(cho, _WAE) + '요'
    if jung == _I:
        return stem[:-1] + _join(cho, _YEO) + '요'
    if jung == _EU:
        previous = stem[-2] if len(stem) >= 2 and _is_hangul(stem[-2]) else None
        if last == '르' and previous and not stem.endswith(_EU_DROP_REU):
            pcho, pjung, pjong = _split(previous)
            if not pjong:
                return stem[:-2] + _join(pcho, pjung, _RIEUL) + ('라요' if pjung in (_A, _O) else '러요')
        bright = previous is not None and _split(previous)[1] in (_A, _O)
        return stem[:-1] + _join(cho, _A if bright else _EO) + '요'
    return stem + '어요'


def _copula(noun):
    """명사 뒤 '이에요/예요' (받침 있으면 이에요)."""
    for ch in reversed(noun):
        if _is_hangul(ch):
            return '이에요' if _split(ch)[2] else '예요'
        if ch.isalnum():
            return '이에요'
    return None


def convert_word(word):
    """'...니다'로 끝나는 어절 하나를 해요체로 바꿉니다. 바꿀 수 없으면 None."""
    if word.endswith('습니다'):
        return conjugate(word[:-3]) if len(word) > 3 else None
    if word.endswith(('아닙니다', '아니랍니다')):
        return word[: word.rindex('아')] + '아니에요'
    if word.endswith('십니다'):  # 높임 '-시-'의 해요체는 '-세요' (이십니다 → 이세요)
        return word[:-3] + '세요' if len(word) > 3 else None
    if len(word) < 3 or not _is_hangul(word[-3]):
        return None
    cho, jung, jong = _split(word[-3])
    if jong != _BIEUP:  # '아니다' 같은 평서형은 그대로
        return None
    syllable = _join(cho, jung)  # 랍 → 라, 입 → 이, 합 → 하 ...
    base = word[:-3]

    if syllable == '이':  # ~입니다
        if not base:
            return None
        if base in _I_VERB_BASES:  # 보입니다 → 보여요
            return conjugate(base + '이')
        if base.endswith('것'):
            return base[:-1] + '거예요'
        copula = _copula(base)
        return base + copula if copula else None
    if syllable == '거':  # ~겁니다 (것입니다)
        return base + '거예요'
    if syllable == '라':  # ~랍니다
        if base.endswith('바'):  # 바랍니다
            return base + '라요'
        if base.endswith('이') and not base.endswith(_I_NOUN_SUFFIXES):
            return base[:-1] + '이에요'
        return base + '예요' if base else None
    if syllable == '다':  # ~답니다
        if not base:
            return None
        if base.endswith('는'):  # 찾는답니다 → 찾아요
            return conjugate(base[:-1]) if len(base) > 1 else None
        bcho, bjung, bjong = _split(base[-1]) if _is_hangul(base[-1]) else (None, None, None)
        if bjong == _NIEUN:  # 보인답니다 → 보이 → 보여요
            stem = base[:-1] + _join(bcho, bjung)
            if stem[-1] in _RIEUL_DROPPED:
                stem = stem[:-1] + _RIEUL_DROPPED[stem[-1]]
            return conjugate(stem)
        return conjugate(base)  # 좋답니다·있답니다·가졌답니다
    return conjugate(base + syllable)  # 합니다·됩니다·줍니다·집니다·큽니다·드립니다·보입니다


def to_haeyo(text):
    """문장 끝 합니다체 어미를 해요체로 바꾼 글을 돌려줍니다."""
    if not text or '니다' not in text:
        return text

    def replace(match):
        converted = convert_word(match.group(1))
        return converted if converted else match.group(1)

    return _TOKEN.sub(replace, text)


# 문장부호 앞 빈칸 ("깊어요 ." → "깊어요.")
_SPACE_BEFORE_PUNCT = re.compile(r'(?<=[가-힣A-Za-z0-9)\'"’”])[ \t]+(?=[.!?](?:\s|$))')


def normalize_copy(text):
    """사전 생성 문구 정리: 문장부호 앞 빈칸을 없애고 어미를 해요체로 맞춥니다."""
    if not text:
        return text
    return to_haeyo(_SPACE_BEFORE_PUNCT.sub('', text))
