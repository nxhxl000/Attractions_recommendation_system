import React, { useState, useEffect } from "react";

interface Recommendation {
  id: number;
  name: string;
  city?: string | null;
  type?: string | null;
  transport?: string | null;
  price?: string | null;
  working_hours?: string | null;
  rating?: number | null;
  image_url?: string | null;
  score: number;
}

interface Recommendations {
  user_id: number;
  recommendations: Recommendation[];
}

interface Props {
  userId: number;
}

const BASE = import.meta.env.VITE_API_URL || "";
const api = (path: string) => (BASE ? `${BASE}${path}` : `/api${path}`);

export default function UserBasedRecommendations({ userId }: Props) {
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!userId) return;

    const fetchRecommendations = async () => {
      setLoading(true);
      setError(null);
      setRecommendations([]);

      try {
        const res = await fetch(api(`/recommend/user/${userId}?top_k=5`));
        if (!res.ok) throw new Error(`Ошибка ${res.status}`);
        const data: Recommendations = await res.json();
        setRecommendations(data.recommendations);
      } catch (e: unknown) {
        setError(
          e instanceof Error ? e.message : "Не удалось загрузить рекомендации"
        );
      } finally {
        setLoading(false);
      }
    };

    fetchRecommendations();
  }, [userId]);

  return (
    <div
      style={{
        width: 380,
        padding: 16,
        border: "1px solid #ccc",
        borderRadius: 8,
        
      }}
    >
      <h3 style={{ marginTop: 0 }}>Пользовательские рекомендации</h3>

      {loading && <p>Загружаем рекомендации…</p>}
      {error && (
        <div
          style={{
            padding: 8,
            backgroundColor: "#fee",
            color: "#c00",
            borderRadius: 4,
          }}
        >
          {error}
        </div>
      )}
      {!loading && recommendations.length === 0 && <p>Нет рекомендаций.</p>}

      {recommendations.map((rec) => (
        <div
          key={rec.id}
          style={{
            border: "1px solid #eee",
            borderRadius: 4,
            padding: 8,
            marginBottom: 8,
            position: "relative",
            backgroundColor: "#f9f9f9",
          }}
        >
          <span
            style={{
              position: "absolute",
              top: 8,
              right: 8,
              backgroundColor: "#007bff",
              color: "white",
              padding: "2px 6px",
              borderRadius: 4,
              fontSize: 12,
            }}
          >
            {rec.score.toFixed(1)}
          </span>

          {rec.image_url && (
            <div
              style={{
                width: "100%",
                height: 120,
                marginBottom: 8,
                borderRadius: 4,
                overflow: "hidden",
                backgroundColor: "#eee",
              }}
            >
              <img
                src={rec.image_url}
                alt={rec.name}
                style={{ width: "100%", height: "100%", objectFit: "cover" }}
              />
            </div>
          )}

          <strong>{rec.name}</strong>
          {rec.city && <div>Город: {rec.city}</div>}
          {rec.type && <div>Тип: {rec.type}</div>}
          {rec.transport && <div>Транспорт: {rec.transport}</div>}
          {rec.price && <div>Цена: {rec.price}</div>}
          {rec.working_hours && <div>Часы работы: {rec.working_hours}</div>}
          {rec.rating !== null && rec.rating !== undefined && (
            <div>Рейтинг: {rec.rating.toFixed(1)}/5</div>
          )}
        </div>
      ))}
    </div>
  );
}
