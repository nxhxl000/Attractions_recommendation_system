import { useState } from "react"
import RecommendationForm from "./RecommendationForm"

type Attraction = { id: number; name: string }

// В dev используем прокси (/api -> http://localhost:8000).
// В prod можно задать переменную окружения VITE_API_URL.
const BASE = import.meta.env.VITE_API_URL || ""
const api = (path: string) => (BASE ? `${BASE}${path}` : `/api${path}`)

export default function App() {
  const [items, setItems] = useState<Attraction[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(api("/attractions"))
      if (!res.ok) {
        const text = await res.text().catch(() => "")
        throw new Error(`Ошибка ${res.status}${text ? `: ${text}` : ""}`)
      }
      const data: Attraction[] = await res.json()
      setItems(data)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Не удалось загрузить данные")
    } finally {
      setLoading(false)
    }
  }

  return (
    <main>
      <h1 style={{ marginBottom: 16 }}>Система рекомендаций достопримечательностей</h1>

      <div style={{ marginBottom: 40 }}>
        <h2 style={{ marginBottom: 16 }}>Список достопримечательностей</h2>
        <button onClick={load} disabled={loading} style={{ marginBottom: 12 }}>
          {loading ? "Загружаю…" : "Загрузить список"}
        </button>

        {error && (
          <p role="alert" style={{ color: "crimson", marginTop: 8 }}>
            {error}
          </p>
        )}

        {!items.length && !loading && !error && (
          <p style={{ opacity: 0.8 }}>Пока пусто. Нажмите «Загрузить список».</p>
        )}

        <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
          {items.map((it) => (
            <li
              key={it.id}
              style={{
                border: "1px solid #3a3a3a",
                borderRadius: 12,
                padding: 12,
                marginTop: 10,
              }}
            >
              <strong>{it.name}</strong>{" "}
              <span style={{ opacity: 0.7 }}>id: {it.id}</span>
            </li>
          ))}
        </ul>
      </div>

      <hr style={{ margin: "40px 0", border: "none", borderTop: "1px solid #ddd" }} />

      <RecommendationForm />
    </main>
  )
}
