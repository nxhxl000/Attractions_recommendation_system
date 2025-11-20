import { useEffect, useState } from "react"

const BASE = import.meta.env.VITE_API_URL || ""
const api = (path: string) => (BASE ? `${BASE}${path}` : `/api${path}`)

export type OnboardingAttraction = {
  id: number
  name: string
  city?: string | null
  type?: string | null
  image_url?: string | null
}

type OnboardingRatingsProps = {
  userId: number
  onDone: () => void   // коллбек, когда всё успешно сохранено
}

// простой селектор звёзд 1–5
function StarSelector({
  value,
  onChange,
}: {
  value: number | undefined
  onChange: (v: number | undefined) => void
}) {
  const handleClick = (v: number) => {
    if (value === v) onChange(undefined) // повторный клик — снять оценку
    else onChange(v)
  }

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
      {[1, 2, 3, 4, 5].map((v) => (
        <button
          key={v}
          type="button"
          onClick={() => handleClick(v)}
          style={{
            background: "none",
            border: "none",
            cursor: "pointer",
            padding: 0,
            fontSize: 24,
            color: value !== undefined && v <= value ? "#ffc107" : "#e0e0e0",
          }}
          aria-label={`${v} звёзд`}
        >
          ★
        </button>
      ))}
      <span style={{ fontSize: 13, color: "#666", marginLeft: 4 }}>
        {value ? `${value}/5` : "Не оценено"}
      </span>
    </div>
  )
}

export default function OnboardingRatings({ userId, onDone }: OnboardingRatingsProps) {
  const [items, setItems] = useState<OnboardingAttraction[]>([])
  const [ratings, setRatings] = useState<Record<number, number | undefined>>({})
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // загрузка 15 случайных достопримечательностей
  useEffect(() => {
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const res = await fetch(api("/onboarding/attractions?limit=15"))
        if (!res.ok) {
          const text = await res.text().catch(() => "")
          throw new Error(`Ошибка ${res.status}${text ? `: ${text}` : ""}`)
        }
        const data: OnboardingAttraction[] = await res.json()
        setItems(data)
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Не удалось загрузить объекты")
      } finally {
        setLoading(false)
      }
    }

    void load()
  }, [])

  const handleSave = async () => {
    const prepared = Object.entries(ratings)
      .filter(([, r]) => r !== undefined)
      .map(([attraction_id, rating]) => ({
        attraction_id: Number(attraction_id),
        rating: rating as number,
      }))

    if (!prepared.length) {
      setError("Поставьте хотя бы одну оценку 🙂")
      return
    }

    setSaving(true)
    setError(null)
    try {
      const res = await fetch(api("/onboarding/ratings"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId,
          ratings: prepared,
        }),
      })

      if (!res.ok) {
        const text = await res.text().catch(() => "")
        throw new Error(`Ошибка сохранения ${res.status}${text ? `: ${text}` : ""}`)
      }

      onDone() // сообщаем App, что онбординг завершён
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Не удалось сохранить оценки")
    } finally {
      setSaving(false)
    }
  }

  return (
    <main
      style={{
        minHeight: "100vh",
        backgroundColor: "#f5f5f5",
        padding: 24,
        boxSizing: "border-box",
      }}
    >
      <div
        style={{
          maxWidth: 1100,
          margin: "0 auto",
          backgroundColor: "#fff",
          borderRadius: 12,
          padding: 24,
          boxShadow: "0 4px 16px rgba(0,0,0,0.08)",
        }}
      >
        <h1 style={{ marginTop: 0, marginBottom: 8, textAlign: "center" }}>
          Настроим рекомендации под вас
        </h1>
        <p
          style={{
            marginTop: 0,
            marginBottom: 24,
            textAlign: "center",
            color: "#555",
          }}
        >
          Оцените несколько достопримечательностей по пятибалльной шкале.
          Это поможет системе лучше подбирать объекты именно для вас.
        </p>

        {loading && <p>Загружаю подборку…</p>}

        {error && (
          <div
            style={{
              marginBottom: 16,
              padding: 10,
              borderRadius: 6,
              backgroundColor: "#ffe8e8",
              color: "#b00020",
              textAlign: "center",
            }}
          >
            {error}
          </div>
        )}

        {!loading && items.length > 0 && (
          <>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
                gap: 16,
                marginBottom: 24,
              }}
            >
              {items.map((attraction) => (
                <div
                  key={attraction.id}
                  style={{
                    border: "1px solid #e1e1e1",
                    borderRadius: 10,
                    backgroundColor: "#fafafa",
                    padding: 12,
                    display: "flex",
                    flexDirection: "column",
                    gap: 8,
                  }}
                >
                  {attraction.image_url && (
                    <div
                      style={{
                        width: "100%",
                        height: 150,
                        borderRadius: 8,
                        overflow: "hidden",
                        backgroundColor: "#f1f3f5",
                      }}
                    >
                      <img
                        src={attraction.image_url}
                        alt={attraction.name}
                        style={{
                          width: "100%",
                          height: "100%",
                          objectFit: "cover",
                          display: "block",
                        }}
                      />
                    </div>
                  )}

                  <h3
                    style={{
                      margin: "4px 0 0",
                      fontSize: 16,
                      textAlign: "center",
                    }}
                  >
                    {attraction.name}
                  </h3>

                  <div
                    style={{
                      fontSize: 13,
                      color: "#555",
                      textAlign: "center",
                    }}
                  >
                    {attraction.city && <div>📍 {attraction.city}</div>}
                    {attraction.type && <div>🏛 {attraction.type}</div>}
                  </div>

                  <div style={{ marginTop: 8, textAlign: "center" }}>
                    <StarSelector
                      value={ratings[attraction.id]}
                      onChange={(value) =>
                        setRatings((prev) => ({ ...prev, [attraction.id]: value }))
                      }
                    />
                  </div>
                </div>
              ))}
            </div>

            <div style={{ textAlign: "center" }}>
              <button
                type="button"
                onClick={handleSave}
                disabled={saving}
                style={{
                  padding: "10px 24px",
                  backgroundColor: saving ? "#a1a1a1" : "#198754",
                  color: "white",
                  border: "none",
                  borderRadius: 6,
                  cursor: saving ? "not-allowed" : "pointer",
                  fontSize: 16,
                }}
              >
                {saving ? "Сохраняю оценки…" : "Сохранить и перейти к рекомендациям"}
              </button>
            </div>
          </>
        )}
      </div>
    </main>
  )
}