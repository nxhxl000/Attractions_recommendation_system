import { useEffect, useState } from "react"

const BASE = import.meta.env.VITE_API_URL || ""
const api = (path: string) => (BASE ? `${BASE}${path}` : `/api${path}`)

type UserInfo = {
  id: number
  username: string
}

export type PlannedAttraction = {
  attraction_id: number
  added_at: string
  id: number
  name: string
  city?: string | null
  type?: string | null
  transport?: string | null
  price?: string | null
  working_hours?: string | null
  rating?: number | null
  image_url?: string | null
}

interface AccountPageProps {
  user: UserInfo
  token: string
  onBack: () => void
}

export default function AccountPage({ user, token, onBack }: AccountPageProps) {
  const [items, setItems] = useState<PlannedAttraction[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const res = await fetch(api(`/users/${user.id}/planned-visits`), {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        })
        if (!res.ok) {
          const text = await res.text().catch(() => "")
          throw new Error(`Ошибка ${res.status}${text ? `: ${text}` : ""}`)
        }
        const data: PlannedAttraction[] = await res.json()
        setItems(data)
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Не удалось загрузить данные")
      } finally {
        setLoading(false)
      }
    }

    void load()
  }, [user.id, token])

  return (
    <main style={{ maxWidth: 1000, margin: "0 auto", padding: 24 }}>
      {/* шапка аккаунта */}
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 24,
          gap: 12,
          flexWrap: "wrap",
        }}
      >
        <div>
          <h1 style={{ margin: 0 }}>Мой аккаунт</h1>
          <p style={{ margin: "4px 0 0", color: "#555" }}>
            Вы вошли как <strong>{user.username}</strong> (id: {user.id})
          </p>
        </div>
        <button
          type="button"
          onClick={onBack}
          style={{
            padding: "8px 16px",
            borderRadius: 4,
            border: "none",
            backgroundColor: "#0d6efd",
            color: "white",
            cursor: "pointer",
            fontSize: 14,
          }}
        >
          ← Назад к списку
        </button>
      </header>

      <section>
        <h2 style={{ marginBottom: 12 }}>Запланированные посещения</h2>

        {loading && <p>Загружаю...</p>}
        {error && <p style={{ color: "crimson" }}>{error}</p>}

        {!loading && !error && items.length === 0 && (
          <p style={{ color: "#666" }}>
            У вас пока нет достопримечательностей в списке «Хочу посетить».
            Выберите их на главной странице.
          </p>
        )}

        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {items.map((item) => (
            <article
              key={item.attraction_id}
              style={{
                display: "flex",
                gap: 16,
                padding: 16,
                borderRadius: 8,
                border: "1px solid #dee2e6",
                backgroundColor: "#f9fafb",
              }}
            >
              {/* Картинка */}
              {item.image_url && (
                <div
                  style={{
                    width: 140,
                    height: 100,
                    borderRadius: 8,
                    overflow: "hidden",
                    flexShrink: 0,
                    backgroundColor: "#f1f3f5",
                  }}
                >
                  <img
                    src={item.image_url}
                    alt={item.name}
                    style={{
                      width: "100%",
                      height: "100%",
                      objectFit: "cover",
                      display: "block",
                    }}
                  />
                </div>
              )}

              {/* Текстовая часть */}
              <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 6 }}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    gap: 8,
                    marginBottom: 4,
                  }}
                >
                  <h3 style={{ margin: 0, fontSize: 18 }}>{item.name}</h3>
                  <span
                    style={{
                      fontSize: 12,
                      color: "#666",
                      whiteSpace: "nowrap",
                    }}
                  >
                    Добавлено:{" "}
                    {new Date(item.added_at).toLocaleString("ru-RU", {
                      day: "2-digit",
                      month: "2-digit",
                      year: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                </div>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                    gap: 6,
                    fontSize: 14,
                  }}
                >
                  {item.city && (
                    <div>
                      <strong>Город:</strong> {item.city}
                    </div>
                  )}
                  {item.type && (
                    <div>
                      <strong>Тип:</strong> {item.type}
                    </div>
                  )}
                  {item.transport && (
                    <div>
                      <strong>Транспорт:</strong> {item.transport}
                    </div>
                  )}
                  {item.price && (
                    <div>
                      <strong>Цена:</strong> {item.price}
                    </div>
                  )}
                  {item.working_hours && (
                    <div>
                      <strong>Часы работы:</strong> {item.working_hours}
                    </div>
                  )}
                  {item.rating !== null && item.rating !== undefined && (
                    <div>
                      <strong>Рейтинг:</strong> {item.rating.toFixed(1)}/5.0
                    </div>
                  )}
                </div>
              </div>
            </article>
          ))}
        </div>
      </section>
    </main>
  )
}