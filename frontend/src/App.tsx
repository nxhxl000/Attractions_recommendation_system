import { useCallback, useEffect, useState } from "react"
import AttractionsList, { type AttractionCardData } from "./AttractionsList"
import RecommendationForm from "./RecommendationForm"
import LoginForm from "./LoginForm"
import OnboardingRatings from "./OnboardingRatings"
import AccountPage from "./AccountPage"


// В dev используем прокси (/api -> http://localhost:8000).
// В prod можно задать переменную окружения VITE_API_URL.
const BASE = import.meta.env.VITE_API_URL || ""
const api = (path: string) => (BASE ? `${BASE}${path}` : `/api${path}`)

export default function App() {
  const [items, setItems] = useState<AttractionCardData[]>([])
  const [plannedIds, setPlannedIds] = useState<number[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showRecommendations, setShowRecommendations] = useState(false)

  // 🔐 токен пользователя
  const [token, setToken] = useState<string | null>(null)
  // 👤 информация о текущем пользователе
  const [currentUser, setCurrentUser] = useState<{ id: number; username: string } | null>(null)
  const [needsOnboarding, setNeedsOnboarding] = useState<boolean | null>(null)
  const [activePage, setActivePage] = useState<"main" | "account">("main")
  // Чтение сохранённых данных при загрузке страницы

  useEffect(() => {
    const savedToken = localStorage.getItem("token")
    const savedUser = localStorage.getItem("currentUser")

    if (savedToken && savedUser) {
      try {
        const parsed = JSON.parse(savedUser) as { id: number; username: string }
        setToken(savedToken)
        setCurrentUser(parsed)
        void fetchRatingsStatus(parsed.id)
      } catch {
        localStorage.removeItem("token")
        localStorage.removeItem("currentUser")
        setNeedsOnboarding(false)
      }
    } else {
      setNeedsOnboarding(false)
    }
  }, [])

  const load = useCallback(async () => {
    if (!token) return // без токена не грузим

    setLoading(true)
    setError(null)
    try {
      const res = await fetch(api("/attractions"), {
        headers: {
          Authorization: `Bearer ${token}`, // backend пока не проверяет, но пусть будет
        },
      })
      if (!res.ok) {
        const text = await res.text().catch(() => "")
        throw new Error(`Ошибка ${res.status}${text ? `: ${text}` : ""}`)
      }
      const data: AttractionCardData[] = await res.json()
      setItems(data)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Не удалось загрузить данные")
    } finally {
      setLoading(false)
    }
  }, [token])

  type PlannedVisitFromApi = {
    attraction_id: number
    // остальные поля нам не нужны для кнопок
  }

  async function fetchPlannedVisits(userId: number, token: string) {
    try {
      const res = await fetch(api(`/users/${userId}/planned-visits`), {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      if (!res.ok) {
        const text = await res.text().catch(() => "")
        throw new Error(`Ошибка ${res.status}${text ? `: ${text}` : ""}`)
      }

      const data: PlannedVisitFromApi[] = await res.json()
      setPlannedIds(data.map((item) => item.attraction_id))
    } catch (e) {
      console.error("Не удалось загрузить запланированные визиты:", e)
    }
  }

  useEffect(() => {
    if (token) {
      void load()
    }
  }, [token, load])

  useEffect(() => {
    if (token && currentUser) {
      void fetchPlannedVisits(currentUser.id, token)
    }
  }, [token, currentUser])

  async function fetchRatingsStatus(userId: number) {
    try {
      const res = await fetch(api(`/users/${userId}/ratings-status`))
      if (!res.ok) throw new Error()
      const data: { has_ratings: boolean; count: number } = await res.json()
      setNeedsOnboarding(!data.has_ratings)
    } catch {
      // если что-то пошло не так — не блокируем пользователя
      setNeedsOnboarding(false)
    }
  }
  // 🚪 если не залогинен — показываем только форму логина
  if (!token || !currentUser) {
    return (
      <LoginForm
        onLoginSuccess={({ token, userId, username }) => {
          setToken(token)
          const user = { id: userId, username }
          setCurrentUser(user)

          localStorage.setItem("token", token)
          localStorage.setItem("currentUser", JSON.stringify(user))

          void fetchRatingsStatus(userId)
          void fetchPlannedVisits(userId, token)
        }}
      />
    )
  }

  async function handleAddPlanned(attractionId: number) {
    if (!currentUser || !token) return

    try {
      const res = await fetch(api("/planned-visits"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          user_id: currentUser.id,
          attraction_id: attractionId,
        }),
      })

      if (!res.ok) {
        const text = await res.text().catch(() => "")
        throw new Error(`Ошибка ${res.status}${text ? `: ${text}` : ""}`)
      }

      await res.json()

      // 👉 отмечаем как запланированную в UI
      setPlannedIds(prev =>
        prev.includes(attractionId) ? prev : [...prev, attractionId]
      )
    } catch (e) {
      console.error("Не удалось добавить в планы:", e)
    }
  }

  async function handleRemovePlanned(attractionId: number) {
    if (!currentUser || !token) return

    try {
      const res = await fetch(api("/planned-visits"), {
        method: "DELETE",                        // см. свой backend
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          user_id: currentUser.id,
          attraction_id: attractionId,
        }),
      })

      if (!res.ok) {
        const text = await res.text().catch(() => "")
        throw new Error(`Ошибка ${res.status}${text ? `: ${text}` : ""}`)
      }

      await res.json()

      // 👉 убираем из локального списка
      setPlannedIds(prev => prev.filter(id => id !== attractionId))
    } catch (e) {
      console.error("Не удалось отменить визит:", e)
    }
  }

  // если нужно пройти онбординг — показываем экран с 15 объектами
  if (needsOnboarding && currentUser) {
    return (
      <OnboardingRatings
        userId={currentUser.id}
        onDone={() => setNeedsOnboarding(false)}
      />
    )
  }

  // 👇 если выбрана страница аккаунта — показываем её вместо главной
  if (activePage === "account") {
    return (
      <AccountPage
        user={currentUser}
        token={token}
        onBack={() => setActivePage("main")}
      />
    )
  }

  console.log(
    "DEBUG App file =", import.meta.url,
    "| typeof handleAddPlanned =", typeof handleAddPlanned
  )

  return (
    <main style={{ position: "relative" }}>
      {currentUser && (
        <div
          style={{
            position: "fixed",
            top: 8,
            left: 16,
            backgroundColor: "#0d6efd",
            color: "white",
            padding: "6px 12px",
            borderRadius: 4,
            fontSize: 14,
            zIndex: 1100,
            display: "flex",
            alignItems: "center",
            gap: 12,
          }}
        >
          <span>
            Вы вошли как <strong>{currentUser.username}</strong> (id: {currentUser.id})
          </span>
          <button
            type="button"
            onClick={() => setActivePage("account")}
            style={{
              padding: "4px 10px",
              backgroundColor: "rgba(255, 255, 255, 0.15)",
              color: "white",
              border: "1px solid rgba(255, 255, 255, 0.5)",
              borderRadius: 4,
              cursor: "pointer",
              fontSize: 13,
              whiteSpace: "nowrap",
            }}
          >
            Мой аккаунт
          </button>
        </div>
      )}

      <h1 style={{ marginBottom: 16, textAlign: "center" }}>
        Система рекомендаций достопримечательностей
      </h1>

      <div style={{ marginBottom: 40 }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: 16,
            marginBottom: 24,
          }}
        >
          <h2 style={{ margin: 0 }}>Список достопримечательностей</h2>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            <button
              onClick={load}
              disabled={loading}
              style={{
                padding: "10px 20px",
                backgroundColor: loading ? "#a1a1a1" : "#198754",
                color: "white",
                border: "none",
                borderRadius: 4,
                cursor: loading ? "not-allowed" : "pointer",
                fontSize: 16,
              }}
            >
              {loading ? "Загружаю…" : "Обновить список"}
            </button>
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
            <button
              onClick={() => {
                setToken(null)
                setCurrentUser(null)
                setItems([])
                setPlannedIds([])
                setActivePage("main")

                // чистим сохранённую сессию
                localStorage.removeItem("token")
                localStorage.removeItem("currentUser")
              }}
              style={{
                padding: "10px 20px",
                backgroundColor: "#dc3545",
                color: "white",
                border: "none",
                borderRadius: 4,
                cursor: "pointer",
                fontSize: 16,
              }}
            >
              Выйти
            </button>
          </div>
        </div>
        <AttractionsList
          items={items}
          loading={loading}
          error={error}
          plannedIds={plannedIds}
          onPlannedClick={handleAddPlanned}
          onCancelPlanned={handleRemovePlanned}
        />
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
              borderRadius: 8,
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
            <RecommendationForm
              plannedIds={plannedIds}
              onPlannedClick={handleAddPlanned}
              onCancelPlanned={handleRemovePlanned}
            />
          </div>
        </div>
      )}
    </main>
  )
}
