const KEY = 'taskflow.ownerId'

let memoryId: string | null = null

function uuidv4(): string {
  // crypto.randomUUID 는 보안 컨텍스트(https, localhost)에서만 있다.
  // 휴대폰에서 개발 서버 주소(http)로 열 때를 위해 getRandomValues 로 만든다.
  const b = crypto.getRandomValues(new Uint8Array(16))
  b[6] = (b[6] & 0x0f) | 0x40
  b[8] = (b[8] & 0x3f) | 0x80
  const h = Array.from(b, (x) => x.toString(16).padStart(2, '0')).join('')
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`
}

export function getOwnerId(): string {
  try {
    const saved = localStorage.getItem(KEY)
    if (saved) return saved
    const id = uuidv4()
    localStorage.setItem(KEY, id)
    return id
  } catch {
    // 저장소를 못 쓰면 이번 방문 동안만 같은 값을 쓴다.
    memoryId ??= uuidv4()
    return memoryId
  }
}
