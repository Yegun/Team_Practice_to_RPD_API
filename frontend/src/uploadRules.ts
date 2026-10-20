import { ApiRequestError, NETWORK_ERROR } from './api'
import { strings } from './strings'

export const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp']
export const MAX_BYTES = 10 * 1024 * 1024

// 서버에 보내기 전에 화면에서 먼저 거른다 (D-018). 서버도 같은 규칙으로 다시 확인한다.
export function checkFile(file: File): string | null {
  if (!ALLOWED_TYPES.includes(file.type)) return strings.uploadErrors.badType
  if (file.size > MAX_BYTES) return strings.uploadErrors.tooLarge
  return null
}

export function uploadErrorMessage(err: unknown): string {
  if (!(err instanceof ApiRequestError)) return strings.uploadErrors.other
  switch (err.code) {
    case 'INVALID_IMAGE':
      return strings.uploadErrors.badType
    case 'IMAGE_TOO_LARGE':
      return strings.uploadErrors.tooLarge
    case NETWORK_ERROR:
      return strings.uploadErrors.network
    case 'AI_FAILED':
      return strings.uploadErrors.aiFailed
    case 'NO_FOOD_FOUND':
      return strings.uploadErrors.noFood
    default:
      return strings.uploadErrors.other
  }
}
