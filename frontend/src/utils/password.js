// Временный пароль: 12 символов без похожих букв + дефис + 2 цифры
export function generatePassword() {
  const alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789'
  const bytes = crypto.getRandomValues(new Uint32Array(12))
  const body = Array.from(bytes, (n) => alphabet[n % alphabet.length]).join('')
  return `${body}-${(bytes[0] % 90) + 10}`
}
