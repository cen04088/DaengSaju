// 공개 동물등록 집계에서 확인된 순서. 순위가 공개되지 않은 29위 대신 31위 빠삐용을 포함한다.
export const DOG_BREEDS = [
  { id: 'maltese', label: '말티즈' },
  { id: 'poodle', label: '푸들' },
  { id: 'pomeranian', label: '포메라니안' },
  { id: 'bichon', label: '비숑 프리제' },
  { id: 'shih-tzu', label: '시추' },
  { id: 'jindo', label: '진돗개' },
  { id: 'yorkshire-terrier', label: '요크셔테리어' },
  { id: 'chihuahua', label: '치와와' },
  { id: 'spitz', label: '스피츠' },
  { id: 'dachshund', label: '닥스훈트' },
  { id: 'cocker-spaniel', label: '코카스패니얼' },
  { id: 'schnauzer', label: '슈나우저' },
  { id: 'golden-retriever', label: '골든리트리버' },
  { id: 'shiba', label: '시바견' },
  { id: 'labrador-retriever', label: '래브라도리트리버' },
  { id: 'welsh-corgi', label: '웰시코기 펨브로크' },
  { id: 'miniature-pinscher', label: '미니어처 핀셔' },
  { id: 'french-bulldog', label: '프렌치불독' },
  { id: 'border-collie', label: '보더콜리' },
  { id: 'pekingese', label: '페키니즈' },
  { id: 'italian-greyhound', label: '이탈리안 그레이하운드' },
  { id: 'pungsan', label: '풍산개' },
  { id: 'coton-de-tulear', label: '꼬똥 드 툴레아' },
  { id: 'beagle', label: '비글' },
  { id: 'boston-terrier', label: '보스턴테리어' },
  { id: 'siberian-husky', label: '시베리안 허스키' },
  { id: 'pug', label: '퍼그' },
  { id: 'shetland-sheepdog', label: '셔틀랜드 쉽독' },
  { id: 'sapsali', label: '삽살개' },
  { id: 'papillon', label: '빠삐용' },
];

const BREED_IDS = new Set(DOG_BREEDS.map(({ id }) => id));

export function dogBreedImage(breed) {
  const id = BREED_IDS.has(breed) ? breed : 'mixed';
  return `./assets/minhwa/breeds/${id}.webp`;
}
