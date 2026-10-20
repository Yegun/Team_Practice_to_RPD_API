// 화면 문구는 SCREEN-SPEC 에서 정해지지 않았다. 임시 문구를 이 파일에 모아 둔다.
export const strings = {
  appTitle: '식품 기한 정리',
  loading: '불러오는 중...',
  emptyList: '남은 식품이 없습니다.',
  loadFailed: '목록을 불러오지 못했습니다.',
  retry: '다시 시도',
  noDueDate: '기한 없음',
  dueToday: '오늘',
  expired: '기한 지남',
  urgent: '임박',
  risky: '주의 식품',
  storage: {
    fridge: '냉장',
    freezer: '냉동',
    room: '실온',
  },
} as const
