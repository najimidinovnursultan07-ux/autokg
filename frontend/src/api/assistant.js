import { api } from './client.js'

// messages: [{ role: 'user' | 'model', text }]
export async function askAssistant(messages) {
  const { data } = await api.post('/assistant/chat/', { messages })
  return data
}
