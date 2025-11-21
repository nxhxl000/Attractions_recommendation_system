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
  evaluated: boolean        // флаг из planned_visits.evaluated
  id: number
  name: string
  city?: string | null
  type?: string | null
  transport?: string | null
  price?: string | null
  working_hours?: string | null
  rating?: number | null     // общий рейтинг объекта (из attractions)
  image_url?: string | null
  user_rating?: number | null // ОЦЕНКА ПОЛЬЗОВАТЕЛЯ (из ratings)
}

interface AccountPageProps {
  user: UserInfo
  token: string
  onBack: () => void
  onCancelPlanned: (attractionId: number) => void   // 👈 новое
}

function renderStarsReadOnly(rating?: number | null) {
  const value = rating ?? 0

  return (
    <span>
      {Array.from({ length: 5 }).map((_, idx) => {
        const starValue = idx + 1
        const filled = starValue <= value
        return (
          <span
            key={starValue}
            style={{
              color: filled ? "#ffc107" : "#e0e0e0",
              fontSize: 16,
              marginRight: 2,
            }}
          >
            ★
          </span>
        )
      })}
    </span>
  )
}

export default function AccountPage({ user, token, onBack, onCancelPlanned }: AccountPageProps) {
  const [items, setItems] = useState<PlannedAttraction[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // оценки пользователя для ещё НЕ оценённых (первичная оценка)
  const [userRatings, setUserRatings] = useState<Record<number, number>>({})
  const [savingId, setSavingId] = useState<number | null>(null)

  // ⚙️ состояние редактирования для ОЦЕНЁННЫХ объектов
  const [editingId, setEditingId] = useState<number | null>(null)
  const [draftRatings, setDraftRatings] = useState<Record<number, number>>({})

  // 👇 НОВОЕ: состояние "отменяю визит" для кнопки
  const [cancelingId, setCancelingId] = useState<number | null>(null)

  async function load() {
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

  useEffect(() => {
    void load()
  }, [user.id, token])

  // запрос на выставление/изменение оценки
  async function handleRate(attractionId: number, rating: number) {
    if (savingId !== null) return // защита от спама кликами

    if (rating < 1 || rating > 5) {
      alert("Оценка должна быть от 1 до 5")
      return
    }

    try {
      setSavingId(attractionId)

      const res = await fetch(
        api(`/users/${user.id}/planned-visits/${attractionId}/rate`),
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ rating }),
        }
      )

      if (!res.ok) {
        const text = await res.text().catch(() => "")
        throw new Error(`Ошибка ${res.status}${text ? `: ${text}` : ""}`)
      }

      await res.json().catch(() => null)

      // 1) локально сохраняем оценку (для блока запланированных)
      setUserRatings(prev => ({ ...prev, [attractionId]: rating }))

      // 2) помечаем объект как оценённый и обновляем user_rating
      setItems(prev =>
        prev.map(item =>
          item.attraction_id === attractionId
            ? { ...item, evaluated: true, user_rating: rating }
            : item
        )
      )
    } catch (e) {
      console.error("Не удалось сохранить оценку:", e)
      alert(
        e instanceof Error
          ? `Не удалось сохранить оценку: ${e.message}`
          : "Не удалось сохранить оценку"
      )
    } finally {
      setSavingId(null)
    }
  }

  // 👇 НОВОЕ: отмена визита (DELETE /planned-visits)
  async function handleCancelPlanned(attractionId: number) {
    if (cancelingId !== null) return

    try {
      setCancelingId(attractionId)

      const res = await fetch(api("/planned-visits"), {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          user_id: user.id,
          attraction_id: attractionId,
        }),
      })

      if (!res.ok) {
        const text = await res.text().catch(() => "")
        throw new Error(`Ошибка ${res.status}${text ? `: ${text}` : ""}`)
      }

      await res.json().catch(() => null)

      // локально убираем из списка
      setItems(prev =>
        prev.filter(item => item.attraction_id !== attractionId)
      )
    } catch (e) {
      console.error("Не удалось отменить визит:", e)
      alert(
        e instanceof Error
          ? `Не удалось отменить визит: ${e.message}`
          : "Не удалось отменить визит"
      )
    } finally {
      setCancelingId(null)
    }
  }

  const plannedItems = items.filter(i => !i.evaluated)
  const evaluatedItems = items.filter(i => i.evaluated)

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

      {/* Блок: запланированные, ещё не оценены */}
      <section style={{ marginBottom: 32 }}>
        <h2 style={{ marginBottom: 12 }}>Запланированные посещения</h2>

        {loading && <p>Загружаю...</p>}
        {error && <p style={{ color: "crimson" }}>{error}</p>}

        {!loading && !error && plannedItems.length === 0 && (
          <p style={{ color: "#666" }}>
            У вас нет неоценённых достопримечательностей в списке «Хочу
            посетить». Оценивайте посещённые объекты — они появятся ниже в
            разделе «Оценено».
          </p>
        )}

        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {plannedItems.map(item => {
            const userRating = userRatings[item.attraction_id]

            return (
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
                <div
                  style={{
                    flex: 1,
                    display: "flex",
                    flexDirection: "column",
                    gap: 6,
                  }}
                >
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

                  {/* Блок оценивания (первичная оценка) */}
                  <div
                    style={{
                      marginTop: 10,
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                      flexWrap: "wrap",
                    }}
                  >
                    <span style={{ fontSize: 14 }}>Моя оценка:</span>
                    <div style={{ display: "flex", gap: 4 }}>
                      {[1, 2, 3, 4, 5].map(value => {
                        const isActive =
                          userRating !== undefined ? value <= userRating : false
                        return (
                          <button
                            key={value}
                            type="button"
                            disabled={savingId === item.attraction_id}
                            onClick={() =>
                              handleRate(item.attraction_id, value)
                            }
                            style={{
                              background: "none",
                              border: "none",
                              cursor:
                                savingId === item.attraction_id
                                  ? "default"
                                  : "pointer",
                              padding: 0,
                              fontSize: 22,
                              color: isActive ? "#ffc107" : "#e0e0e0",
                            }}
                            aria-label={`Поставить оценку ${value} звезд`}
                          >
                            ★
                          </button>
                        )
                      })}
                    </div>
                    {savingId === item.attraction_id && (
                      <span
                        style={{ fontSize: 12, color: "#666", marginLeft: 4 }}
                      >
                        Сохраняю...
                      </span>
                    )}
                  </div>

                  {/* 👇 НОВЫЙ БЛОК: "Посещение запланировано!" + кнопка "Отменить визит" */}
                  <div
                    style={{
                      marginTop: 10,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "flex-end",
                      gap: 8,
                      flexWrap: "wrap",
                    }}
                  >
                    <span
                      style={{
                        color: "#198754",
                        fontSize: 13,
                        fontWeight: 500,
                      }}
                    >
                      Посещение запланировано!
                    </span>
                    <button
                      type="button"
                      onClick={() => {
                        onCancelPlanned(item.attraction_id)                     // 👈 обновляем plannedIds в App
                        setItems(prev => prev.filter(i => i.attraction_id !== item.attraction_id)) // 👈 локально убираем из списка
                      }}
                      style={{
                        padding: "6px 12px",
                        borderRadius: 4,
                        border: "none",
                        backgroundColor: "#dc3545",
                        color: "#fff",
                        cursor: "pointer",
                        fontSize: 13,
                        boxShadow: "0 2px 4px rgba(0,0,0,0.15)",
                      }}
                    >
                      Отменить визит
                    </button>
                  </div>
                </div>
              </article>
            )
          })}
        </div>
      </section>

      {/* Блок: уже оценённые объекты */}
      <section>
        <h2 style={{ marginBottom: 12 }}>Оценено</h2>

        {evaluatedItems.length === 0 && (
          <p style={{ color: "#666" }}>
            Здесь появятся объекты, которые вы уже оценили.
          </p>
        )}

        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {evaluatedItems.map(item => {
            const isEditing = editingId === item.attraction_id
            const draft = draftRatings[item.attraction_id]
            const displayRating =
              (isEditing ? draft : item.user_rating) ?? 0

            return (
              <article
                key={item.attraction_id}
                style={{
                  display: "flex",
                  gap: 16,
                  padding: 16,
                  borderRadius: 8,
                  border: "1px solid #dee2e6",
                  backgroundColor: "#f1fff3",
                }}
              >
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

                <div
                  style={{
                    flex: 1,
                    display: "flex",
                    flexDirection: "column",
                    gap: 6,
                  }}
                >
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
                        <strong>Общий рейтинг:</strong>{" "}
                        {item.rating.toFixed(1)}/5.0
                      </div>
                    )}
                  </div>

                  {/* ⭐ Моя оценка + кнопки "Изменить"/"Сохранить" */}
                  <div
                    style={{
                      marginTop: 8,
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                      fontSize: 14,
                      flexWrap: "wrap",
                    }}
                  >
                    <strong>Моя оценка:</strong>
                    {isEditing ? (
                      <div style={{ display: "flex", gap: 4 }}>
                        {[1, 2, 3, 4, 5].map(value => {
                          const active = value <= displayRating
                          return (
                            <button
                              key={value}
                              type="button"
                              disabled={savingId === item.attraction_id}
                              onClick={() =>
                                setDraftRatings(prev => ({
                                  ...prev,
                                  [item.attraction_id]: value,
                                }))
                              }
                              style={{
                                background: "none",
                                border: "none",
                                cursor:
                                  savingId === item.attraction_id
                                    ? "default"
                                    : "pointer",
                                padding: 0,
                                fontSize: 22,
                                color: active ? "#ffc107" : "#e0e0e0",
                              }}
                              aria-label={`Изменить оценку на ${value} звезд`}
                            >
                              ★
                            </button>
                          )
                        })}
                      </div>
                    ) : (
                      <>
                        {renderStarsReadOnly(item.user_rating)}
                        {item.user_rating != null && (
                          <span style={{ color: "#555", fontSize: 13 }}>
                            {item.user_rating.toFixed(1)}/5.0
                          </span>
                        )}
                      </>
                    )}

                    <button
                      type="button"
                      disabled={savingId === item.attraction_id}
                      onClick={async () => {
                        if (!isEditing) {
                          // включаем режим редактирования
                          setEditingId(item.attraction_id)
                          setDraftRatings(prev => ({
                            ...prev,
                            [item.attraction_id]: item.user_rating ?? 0,
                          }))
                        } else {
                          // сохраняем новую оценку
                          const newRating =
                            draftRatings[item.attraction_id] ??
                            item.user_rating ??
                            0
                          await handleRate(item.attraction_id, newRating)
                          setEditingId(null)
                        }
                      }}
                      style={{
                        padding: "6px 12px",
                        borderRadius: 4,
                        border: "none",
                        backgroundColor: isEditing ? "#198754" : "#0d6efd",
                        color: "#fff",
                        cursor: "pointer",
                        fontSize: 13,
                        marginLeft: 8,
                      }}
                    >
                      {isEditing ? "Сохранить" : "Изменить"}
                    </button>
                  </div>

                  <div style={{ marginTop: 8, fontSize: 13, color: "#198754" }}>
                    ✓ Оценено пользователем
                  </div>
                </div>
              </article>
            )
          })}
        </div>
      </section>
    </main>
  )
}
