import { useState } from "react"
import type { FormEvent } from "react"

function StarRatingSelector({
  rating,
  onRatingChange,
}: {
  rating: number | undefined
  onRatingChange: (rating: number | undefined) => void
}) {
  const handleStarClick = (value: number) => {
    // If clicking the same star, clear the rating
    if (rating === value) {
      onRatingChange(undefined)
    } else {
      onRatingChange(value)
    }
  }


  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div style={{ display: "flex", gap: 4 }}>
        {[1, 2, 3, 4, 5].map((value) => {
          const isSelected = rating !== undefined && value <= rating
          return (
            <button
              key={value}
              type="button"
              onClick={() => handleStarClick(value)}
              style={{
                background: "none",
                border: "none",
                cursor: "pointer",
                padding: 4,
                fontSize: 28,
                color: isSelected ? "#ffc107" : "#e0e0e0",
                transition: "transform 0.1s ease",
              }}
              onMouseOver={(e) => {
                e.currentTarget.style.transform = "scale(1.1)"
              }}
              onMouseOut={(e) => {
                e.currentTarget.style.transform = "scale(1)"
              }}
              aria-label={`Минимальный рейтинг ${value} звезд`}
            >
              ★
            </button>
          )
        })}
      </div>
      {rating !== undefined && (
        <span style={{ fontSize: 14, color: "#666", marginLeft: 4 }}>
          {rating.toFixed(1)}+
        </span>
      )}
      {rating === undefined && (
        <span style={{ fontSize: 14, color: "#999", marginLeft: 4, fontStyle: "italic" }}>
          Не выбрано
        </span>
      )}
    </div>
  )
}

type RecommendationRequest = {
  city?: string
  type?: string
  transport?: string
  price?: string
  desired_period: string
  min_rating?: number
  top_k: number
}

type RecommendationResult = {
  id: number
  name: string
  city?: string | null
  type?: string | null
  transport?: string | null
  price?: string | null
  working_hours?: string | null
  rating?: number | null
  score: number
}

const BASE = import.meta.env.VITE_API_URL || ""
const api = (path: string) => (BASE ? `${BASE}${path}` : `/api${path}`)

export default function RecommendationForm() {
  const [formData, setFormData] = useState<RecommendationRequest>({
    city: "",
    type: "",
    transport: "",
    price: "",
    desired_period: "anytime",
    min_rating: undefined,
    top_k: 5,
  })
  const [results, setResults] = useState<RecommendationResult[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setResults([])

    try {
      // Prepare request payload (only include non-empty fields)
      const payload: RecommendationRequest = {
        desired_period: formData.desired_period,
        top_k: formData.top_k,
      }
      if (formData.city?.trim()) payload.city = formData.city.trim()
      if (formData.type?.trim()) payload.type = formData.type.trim()
      if (formData.transport?.trim()) payload.transport = formData.transport.trim()
      if (formData.price?.trim()) payload.price = formData.price.trim()
      if (formData.min_rating !== undefined && formData.min_rating > 0) {
        payload.min_rating = formData.min_rating
      }

      const res = await fetch(api("/recommendations"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      })

      if (!res.ok) {
        const text = await res.text().catch(() => "")
        throw new Error(`Ошибка ${res.status}${text ? `: ${text}` : ""}`)
      }

      const data: RecommendationResult[] = await res.json()
      setResults(data)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Не удалось получить рекомендации")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: 800, margin: "0 auto", padding: 20 }}>
      <h2 style={{ marginBottom: 20 }}>Получить рекомендации</h2>

      <form onSubmit={handleSubmit} style={{ marginBottom: 30 }}>
        <div style={{ display: "grid", gap: 16, marginBottom: 16 }}>
          <div>
            <label htmlFor="city" style={{ display: "block", marginBottom: 4 }}>
              Город (необязательно)
            </label>
            <input
              id="city"
              type="text"
              value={formData.city}
              onChange={(e) => setFormData({ ...formData, city: e.target.value })}
              placeholder="Например: Москва"
              style={{
                width: "100%",
                padding: 8,
                borderRadius: 4,
                border: "1px solid #ccc",
                boxSizing: "border-box",
              }}
            />
          </div>

          <div>
            <label htmlFor="type" style={{ display: "block", marginBottom: 4 }}>
              Тип достопримечательности (необязательно)
            </label>
            <input
              id="type"
              type="text"
              value={formData.type}
              onChange={(e) => setFormData({ ...formData, type: e.target.value })}
              placeholder="Например: Современная, Историческая"
              style={{
                width: "100%",
                padding: 8,
                borderRadius: 4,
                border: "1px solid #ccc",
                boxSizing: "border-box",
              }}
            />
          </div>

          <div>
            <label htmlFor="transport" style={{ display: "block", marginBottom: 4 }}>
              Транспорт (необязательно)
            </label>
            <input
              id="transport"
              type="text"
              value={formData.transport}
              onChange={(e) => setFormData({ ...formData, transport: e.target.value })}
              placeholder="Например: Пешком, Метро, Автобус"
              style={{
                width: "100%",
                padding: 8,
                borderRadius: 4,
                border: "1px solid #ccc",
                boxSizing: "border-box",
              }}
            />
          </div>

          <div>
            <label htmlFor="price" style={{ display: "block", marginBottom: 4 }}>
              Цена (необязательно)
            </label>
            <select
              id="price"
              value={formData.price}
              onChange={(e) => setFormData({ ...formData, price: e.target.value })}
              style={{
                width: "100%",
                padding: 8,
                borderRadius: 4,
                border: "1px solid #ccc",
                boxSizing: "border-box",
              }}
            >
              <option value="">Не выбрано</option>
              <option value="Бесплатно">Бесплатно</option>
              <option value="Платно">Платно</option>
            </select>
          </div>

          <div>
            <label htmlFor="desired_period" style={{ display: "block", marginBottom: 4 }}>
              Желаемое время посещения
            </label>
            <select
              id="desired_period"
              value={formData.desired_period}
              onChange={(e) => setFormData({ ...formData, desired_period: e.target.value })}
              style={{
                width: "100%",
                padding: 8,
                borderRadius: 4,
                border: "1px solid #ccc",
                boxSizing: "border-box",
              }}
            >
              <option value="anytime">В любое время</option>
              <option value="morning">Утро (6-11)</option>
              <option value="afternoon">День (12-16)</option>
              <option value="evening">Вечер (17-21)</option>
              <option value="night">Ночь (22-5)</option>
            </select>
          </div>

          <div>
            <label htmlFor="min_rating" style={{ display: "block", marginBottom: 8 }}>
              Минимальный рейтинг (необязательно)
            </label>
            <div
              style={{
                width: "100%",
                padding: "12px",
                border: "1px solid #ccc",
                borderRadius: 4,
                backgroundColor: "#fafafa",
                boxSizing: "border-box",
              }}
            >
              <StarRatingSelector
                rating={formData.min_rating}
                onRatingChange={(rating) =>
                  setFormData({
                    ...formData,
                    min_rating: rating,
                  })
                }
              />
            </div>
            <p style={{ fontSize: 12, color: "#666", marginTop: 4, marginBottom: 0 }}>
              Нажмите на звезду, чтобы установить минимальный рейтинг. Повторный клик снимает выбор.
            </p>
          </div>

          <div>
            <label htmlFor="top_k" style={{ display: "block", marginBottom: 4 }}>
              Количество рекомендаций
            </label>
            <input
              id="top_k"
              type="number"
              min="1"
              max="50"
              value={formData.top_k}
              onChange={(e) =>
                setFormData({ ...formData, top_k: parseInt(e.target.value) || 5 })
              }
              style={{
                width: "100%",
                padding: 8,
                borderRadius: 4,
                border: "1px solid #ccc",
                boxSizing: "border-box",
              }}
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          style={{
            padding: "10px 20px",
            backgroundColor: loading ? "#ccc" : "#007bff",
            color: "white",
            border: "none",
            borderRadius: 4,
            cursor: loading ? "not-allowed" : "pointer",
            fontSize: 16,
          }}
        >
          {loading ? "Загружаю..." : "Получить рекомендации"}
        </button>
      </form>

      {error && (
        <div
          role="alert"
          style={{
            padding: 12,
            backgroundColor: "#fee",
            color: "#c00",
            borderRadius: 4,
            marginBottom: 20,
          }}
        >
          {error}
        </div>
      )}

      {results.length > 0 && (
        <div>
          <h3 style={{ marginBottom: 16 }}>Результаты ({results.length}):</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {results.map((result) => (
              <div
                key={result.id}
                style={{
                  border: "1px solid #ddd",
                  borderRadius: 8,
                  padding: 16,
                  backgroundColor: "#f9f9f9",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                  <h4 style={{ margin: 0, fontSize: 18 }}>{result.name}</h4>
                  <span
                    style={{
                      backgroundColor: "#007bff",
                      color: "white",
                      padding: "4px 8px",
                      borderRadius: 4,
                      fontSize: 12,
                    }}
                  >
                    Схожесть: {(result.score * 100).toFixed(1)}%
                  </span>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 8, fontSize: 14 }}>
                  {result.city && (
                    <div>
                      <strong>Город:</strong> {result.city}
                    </div>
                  )}
                  {result.type && (
                    <div>
                      <strong>Тип:</strong> {result.type}
                    </div>
                  )}
                  {result.transport && (
                    <div>
                      <strong>Транспорт:</strong> {result.transport}
                    </div>
                  )}
                  {result.price && (
                    <div>
                      <strong>Цена:</strong> {result.price}
                    </div>
                  )}
                  {result.working_hours && (
                    <div>
                      <strong>Часы работы:</strong> {result.working_hours}
                    </div>
                  )}
                  {result.rating !== null && result.rating !== undefined && (
                    <div>
                      <strong>Рейтинг:</strong> {result.rating.toFixed(1)}/5.0
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

