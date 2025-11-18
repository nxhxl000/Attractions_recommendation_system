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
  const [showRecommendations, setShowRecommendations] = useState(false)

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
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <h2 style={{ margin: 0 }}>Список достопримечательностей</h2>
          <button
            onClick={() => setShowRecommendations(true)}
            style={{
              padding: "10px 20px",
              backgroundColor: "#007bff",
              color: "white",
              border: "none",
              borderRadius: 4,
              cursor: "pointer",
              fontSize: 16,
            }}
          >
            Получить рекомендации
          </button>
        </div>
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

      {showRecommendations && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(0, 0, 0, 0.5)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: 20,
          }}
          onClick={() => setShowRecommendations(false)}
        >
          <div
            style={{
              backgroundColor: "white",
              borderTopRightRadius: 8,
              borderBottomRightRadius: 8,
              borderTopLeftRadius: 8,
              borderBottomLeftRadius: 8,
              padding: 24,
              maxWidth: 900,
              maxHeight: "90vh",
              overflow: "auto",
              position: "relative",
              width: "100%",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={() => setShowRecommendations(false)}
              style={{
                position: "absolute",
                top: 8,
                right: 8,
                backgroundColor: "#f0f0f0",
                border: "none",
                borderRadius: "60%",
                width: 32,
                height: 32,
                cursor: "pointer",
                fontSize: 15,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                lineHeight: 1,
              }}
              aria-label="Закрыть"
            >
              ×
            </button>
            <RecommendationForm />
          </div>
        </div>
      )}
    </main>
  )
}
