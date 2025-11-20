import { useState } from "react"

const BASE = import.meta.env.VITE_API_URL || ""
const api = (path: string) => (BASE ? `${BASE}${path}` : `/api${path}`)

interface LoginFormProps {
  onLoginSuccess: (data: {
    token: string
    userId: number
    username: string
  }) => void
}

export default function LoginForm({ onLoginSuccess }: LoginFormProps) {
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showPassword, setShowPassword] = useState(false)

  // режим: false = вход, true = регистрация
  const [isRegisterMode, setIsRegisterMode] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      const endpoint = isRegisterMode ? "/auth/register" : "/auth/login"

      const res = await fetch(api(endpoint), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      })

      if (!res.ok) {
        const text = await res.text().catch(() => "")
        throw new Error(
          `${isRegisterMode ? "Ошибка регистрации" : "Ошибка входа"} ${
            res.status
          }${text ? `: ${text}` : ""}`,
        )
      }

      // Оба эндпоинта возвращают формат:
      // { access_token, token_type, user_id, username }
      const data: {
        access_token: string
        token_type: string
        user_id: number
        username: string
      } = await res.json()

      if (!data.access_token) {
        throw new Error("Сервер не вернул токен")
      }

      onLoginSuccess({
        token: data.access_token,
        userId: data.user_id,
        username: data.username,
      })
    
    } finally {
      setLoading(false)
    }
  }

  const toggleMode = () => {
    setError(null)
    setIsRegisterMode((prev) => !prev)
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "#f5f5f5",
        padding: 16,
      }}
    >
      <form
        onSubmit={handleSubmit}
        style={{
          backgroundColor: "white",
          padding: 24,
          borderRadius: 8,
          boxShadow: "0 2px 10px rgba(0,0,0,0.1)",
          width: "100%",
          maxWidth: 400,
        }}
      >
        <h1 style={{ marginTop: 0, marginBottom: 16 }}>
          {isRegisterMode
            ? "Регистрация в системе рекомендаций"
            : "Вход в систему рекомендаций"}
        </h1>

        <div style={{ marginBottom: 12 }}>
          <label style={{ display: "block", marginBottom: 4 }}>Логин</label>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            style={{ width: "100%", padding: 8, boxSizing: "border-box" }}
            required
          />
        </div>

        <div style={{ marginBottom: 16 }}>
            <label style={{ display: "block", marginBottom: 4 }}>Пароль</label>
            <div style={{ position: "relative" }}>
                <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                style={{
                    width: "100%",
                    padding: "8px 36px 8px 8px", // справа место под кнопку-глаз
                    boxSizing: "border-box",
                }}
                required
                />
                <button
                type="button"
                onClick={() => setShowPassword((prev) => !prev)}
                style={{
                    position: "absolute",
                    right: 8,
                    top: "50%",
                    transform: "translateY(-50%)",
                    border: "none",
                    background: "transparent",
                    cursor: "pointer",
                    padding: 0,
                    fontSize: 16,
                }}
                aria-label={showPassword ? "Скрыть пароль" : "Показать пароль"}
                >
                {showPassword ? "🙈" : "👁️"}
                </button>
            </div>
        </div>

        {error && (
          <div style={{ color: "red", marginBottom: 12, fontSize: 14 }}>
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          style={{
            width: "100%",
            padding: "10px 16px",
            backgroundColor: loading ? "#a1a1a1" : "#007bff",
            color: "white",
            border: "none",
            borderRadius: 4,
            cursor: loading ? "not-allowed" : "pointer",
            fontSize: 16,
            marginBottom: 8,
          }}
        >
          {loading
            ? isRegisterMode
              ? "Регистрирую…"
              : "Вхожу…"
            : isRegisterMode
            ? "Зарегистрироваться"
            : "Войти"}
        </button>

        <div
          style={{
            textAlign: "center",
            fontSize: 14,
          }}
        >
          {isRegisterMode ? (
            <>
              Уже есть аккаунт?{" "}
              <button
                type="button"
                onClick={toggleMode}
                style={{
                  background: "none",
                  border: "none",
                  padding: 0,
                  margin: 0,
                  color: "#007bff",
                  cursor: "pointer",
                  textDecoration: "underline",
                  fontSize: 14,
                }}
              >
                Войти
              </button>
            </>
          ) : (
            <>
              Нет аккаунта?{" "}
              <button
                type="button"
                onClick={toggleMode}
                style={{
                  background: "none",
                  border: "none",
                  padding: 0,
                  margin: 0,
                  color: "#007bff",
                  cursor: "pointer",
                  textDecoration: "underline",
                  fontSize: 14,
                }}
              >
                Зарегистрироваться
              </button>
            </>
          )}
        </div>
      </form>
    </div>
  )
}
