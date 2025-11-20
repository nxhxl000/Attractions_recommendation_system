import { Fragment, useState, useMemo, useEffect } from "react"
import "./App.css"

export type AttractionCardData = {
  id: number
  name: string
  city?: string | null
  type?: string | null
  transport?: string | null
  price?: string | null
  working_hours?: string | null
  rating?: number | null
  image_url?: string | null   
  score?: number
}

type AttractionsListProps = {
  items: AttractionCardData[]
  loading: boolean
  error: string | null
  plannedIds: number[]                     // 👈 добавили
  onPlannedClick: (attractionId: number) => void
  onCancelPlanned: (attractionId: number) => void
}

const ITEMS_PER_PAGE = 10

const detailFields: Array<{ label: string; key: keyof AttractionCardData }> = [
  { label: "Транспорт", key: "transport" },
  { label: "Цена", key: "price" },
  { label: "Часы работы", key: "working_hours" },
]

function StarRating({ rating }: { rating: number }) {
  const fullStars = Math.floor(rating)
  const hasHalfStar = rating % 1 >= 0.5
  const emptyStars = 5 - fullStars - (hasHalfStar ? 1 : 0)

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
      {Array.from({ length: fullStars }).map((_, i) => (
        <span key={`full-${i}`} style={{ color: "#ffc107", fontSize: 18 }}>★</span>
      ))}
      {hasHalfStar && (
        <span style={{ color: "#ffc107", fontSize: 18 }}>☆</span>
      )}
      {Array.from({ length: emptyStars }).map((_, i) => (
        <span key={`empty-${i}`} style={{ color: "#e0e0e0", fontSize: 18 }}>★</span>
      ))}
      <span style={{ marginLeft: 6, fontSize: 14, color: "#666" }}>
        {rating.toFixed(1)}
      </span>
    </div>
  )
}

type SortOption = "name-asc" | "name-desc" | "rating-asc" | "rating-desc" | "city-asc" | "city-desc" | "type-asc" | "type-desc" | "none"

export default function AttractionsList({
  items,
  loading,
  error,
  plannedIds,
  onPlannedClick,
  onCancelPlanned,
}: AttractionsListProps) {
  console.log(
    "DEBUG AttractionsList file =", import.meta.url,
    "| typeof onPlannedClick =", typeof onPlannedClick
  )
  const [currentPage, setCurrentPage] = useState(1)
  const [displayedCount, setDisplayedCount] = useState(ITEMS_PER_PAGE) // For "load more" mode
  const [paginationMode, setPaginationMode] = useState<"pages" | "load-more">("pages")

  // Sorting and filtering state
  const [sortBy, setSortBy] = useState<SortOption>("none")
  const [filterCity, setFilterCity] = useState<string>("")
  const [filterType, setFilterType] = useState<string>("")
  const [filterPrice, setFilterPrice] = useState<string>("")
  const [filterMinRating, setFilterMinRating] = useState<number | undefined>(undefined)
  const [showFilters, setShowFilters] = useState(false)

  // Get unique values for filter dropdowns
  const uniqueCities = useMemo(() => {
    const cities = items.map(item => item.city).filter((city): city is string => Boolean(city))
    return Array.from(new Set(cities)).sort()
  }, [items])

  const uniqueTypes = useMemo(() => {
    const types = items
      .flatMap(item =>
        item.type ? item.type.split(",").map(t => t.trim().toLowerCase()) : []
      )
    return Array.from(new Set(types)).sort()
  }, [items])

  // Apply filters and sorting
  const filteredAndSortedItems = useMemo(() => {
    let result = [...items]

    // Apply filters
    if (filterCity) {
      result = result.filter(item => item.city === filterCity)
    }
    if (filterType) {
      result = result.filter(item =>
        item.type?.toLowerCase().includes(filterType.toLowerCase())
      )
    }

    if (filterPrice) {
      result = result.filter(item => item.price === filterPrice)
    }
    if (filterMinRating !== undefined) {
      result = result.filter(item => item.rating !== null && item.rating !== undefined && item.rating >= filterMinRating)
    }

    // Apply sorting
    if (sortBy !== "none") {
      result.sort((a, b) => {
        switch (sortBy) {
          case "name-asc":
            return (a.name || "").localeCompare(b.name || "")
          case "name-desc":
            return (b.name || "").localeCompare(a.name || "")
          case "rating-asc":
            return (a.rating ?? 0) - (b.rating ?? 0)
          case "rating-desc":
            return (b.rating ?? 0) - (a.rating ?? 0)
          case "city-asc":
            return (a.city || "").localeCompare(b.city || "")
          case "city-desc":
            return (b.city || "").localeCompare(a.city || "")
          case "type-asc":
            return (a.type || "").localeCompare(b.type || "")
          case "type-desc":
            return (b.type || "").localeCompare(a.type || "")
          default:
            return 0
        }
      })
    }

    return result
  }, [items, filterCity, filterType, filterPrice, filterMinRating, sortBy])

  // Calculate pagination based on filtered items
  const totalPages = useMemo(() => Math.ceil(filteredAndSortedItems.length / ITEMS_PER_PAGE), [filteredAndSortedItems.length])

  // Get items to display based on mode
  const displayedItems = useMemo(() => {
    if (paginationMode === "pages") {
      const startIndex = (currentPage - 1) * ITEMS_PER_PAGE
      const endIndex = startIndex + ITEMS_PER_PAGE
      return filteredAndSortedItems.slice(startIndex, endIndex)
    } else {
      // Load more mode - show items up to displayedCount
      return filteredAndSortedItems.slice(0, displayedCount)
    }
  }, [filteredAndSortedItems, currentPage, displayedCount, paginationMode])

  const hasMore = paginationMode === "load-more" ? displayedCount < filteredAndSortedItems.length : currentPage < totalPages
  const canGoPrevious = paginationMode === "pages" && currentPage > 1

  const handleLoadMore = () => {
    setDisplayedCount((prev) => Math.min(prev + ITEMS_PER_PAGE, filteredAndSortedItems.length))
  }

  const handleResetFilters = () => {
    setFilterCity("")
    setFilterType("")
    setFilterPrice("")
    setFilterMinRating(undefined)
    setSortBy("none")
    setCurrentPage(1)
    setDisplayedCount(ITEMS_PER_PAGE)
  }

  const hasActiveFilters = filterCity || filterType || filterPrice || filterMinRating !== undefined || sortBy !== "none"

  const handlePrevious = () => {
    setCurrentPage((prev) => Math.max(1, prev - 1))
  }

  const handleNext = () => {
    setCurrentPage((prev) => Math.min(totalPages, prev + 1))
  }

  const handleGoToPage = (page: number) => {
    const pageNum = Math.max(1, Math.min(totalPages, page))
    setCurrentPage(pageNum)
  }

  // Calculate which page numbers to show
  const getPageNumbers = () => {
    const delta = 2 // Show 2 pages on each side of current
    const pages: (number | string)[] = []

    if (totalPages <= 7) {
      // Show all pages if 7 or fewer
      for (let i = 1; i <= totalPages; i++) {
        pages.push(i)
      }
    } else {
      // Always show first page
      pages.push(1)

      if (currentPage > delta + 2) {
        pages.push("...")
      }

      // Show pages around current
      const start = Math.max(2, currentPage - delta)
      const end = Math.min(totalPages - 1, currentPage + delta)

      for (let i = start; i <= end; i++) {
        pages.push(i)
      }

      if (currentPage < totalPages - delta - 1) {
        pages.push("...")
      }

      // Always show last page
      pages.push(totalPages)
    }

    return pages
  }

  // Reset pagination when items or filters change
  useEffect(() => {
    setCurrentPage(1)
    setDisplayedCount(ITEMS_PER_PAGE)
  }, [items.length, filterCity, filterType, filterPrice, filterMinRating, sortBy])

  return (
    <section style={{ minHeight: "1000px", display: "flex", flexDirection: "column" }}>
      {error && (
        <p role="alert" style={{ color: "crimson", marginBottom: 16 }}>
          {error}
        </p>
      )}

      {!items.length && !loading && !error && (
        <p style={{ opacity: 0.75 }}>Пока нет данных. Нажмите «Обновить список», чтобы загрузить.</p>
      )}

      {/* Sorting and Filtering Controls */}
      {items.length > 0 && (
        <div
          style={{
            marginBottom: 16,
            padding: "16px",
            backgroundColor: "#f8f9fa",
            borderRadius: 8,
            border: "1px solid #dee2e6",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: showFilters ? 16 : 0,
              flexWrap: "wrap",
              gap: 12,
            }}
          >
            <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
              <label style={{ fontSize: 14, fontWeight: 500, display: "flex", alignItems: "center", gap: 8 }}>
                Сортировка:
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as SortOption)}
                  style={{
                    padding: "6px 12px",
                    borderRadius: 4,
                    border: "1px solid #ccc",
                    fontSize: 14,
                    cursor: "pointer",
                  }}
                >
                  <option value="none">Без сортировки</option>
                  <option value="name-asc">Название (А-Я)</option>
                  <option value="name-desc">Название (Я-А)</option>
                  <option value="rating-desc">Рейтинг (высокий → низкий)</option>
                  <option value="rating-asc">Рейтинг (низкий → высокий)</option>
                  <option value="city-asc">Город (А-Я)</option>
                  <option value="city-desc">Город (Я-А)</option>
                  <option value="type-asc">Тип (А-Я)</option>
                  <option value="type-desc">Тип (Я-А)</option>
                </select>
              </label>

              <button
                type="button"
                onClick={() => setShowFilters(!showFilters)}
                style={{
                  padding: "6px 12px",
                  backgroundColor: showFilters ? "#007bff" : "#e9ecef",
                  color: showFilters ? "white" : "#495057",
                  border: "none",
                  borderRadius: 4,
                  cursor: "pointer",
                  fontSize: 14,
                }}
              >
                {showFilters ? "▼ Скрыть фильтры" : "▶ Показать фильтры"}
              </button>

              {hasActiveFilters && (
                <button
                  type="button"
                  onClick={handleResetFilters}
                  style={{
                    padding: "6px 12px",
                    backgroundColor: "#dc3545",
                    color: "white",
                    border: "none",
                    borderRadius: 4,
                    cursor: "pointer",
                    fontSize: 14,
                  }}
                >
                  Сбросить фильтры
                </button>
              )}
            </div>

            <div style={{ fontSize: 14, color: "#666" }}>
              Показано: {filteredAndSortedItems.length} из {items.length}
            </div>
          </div>

          {showFilters && (
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
                gap: 12,
                paddingTop: 16,
                borderTop: "1px solid #dee2e6",
              }}
            >
              <div>
                <label style={{ display: "block", fontSize: 13, fontWeight: 500, marginBottom: 4 }}>
                  Город:
                </label>
                <select
                  value={filterCity}
                  onChange={(e) => setFilterCity(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "6px 8px",
                    borderRadius: 4,
                    border: "1px solid #ccc",
                    fontSize: 14,
                    cursor: "pointer",
                    boxSizing: "border-box",
                  }}
                >
                  <option value="">Все города</option>
                  {uniqueCities.map((city) => (
                    <option key={city} value={city}>
                      {city}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ display: "block", fontSize: 13, fontWeight: 500, marginBottom: 4 }}>
                  Тип:
                </label>
                <select
                  value={filterType}
                  onChange={(e) => setFilterType(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "6px 8px",
                    borderRadius: 4,
                    border: "1px solid #ccc",
                    fontSize: 14,
                    cursor: "pointer",
                    boxSizing: "border-box",
                  }}
                >
                  <option value="">Все типы</option>
                  {uniqueTypes.map((type) => (
                    <option key={type} value={type}>
                      {type}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ display: "block", fontSize: 13, fontWeight: 500, marginBottom: 4 }}>
                  Цена:
                </label>
                <select
                  value={filterPrice}
                  onChange={(e) => setFilterPrice(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "6px 8px",
                    borderRadius: 4,
                    border: "1px solid #ccc",
                    fontSize: 14,
                    cursor: "pointer",
                    boxSizing: "border-box",
                  }}
                >
                  <option value="">Все цены</option>
                  <option value="Бесплатно">Бесплатно</option>
                  <option value="Платно">Платно</option>
                </select>
              </div>

              <div>
                <label style={{ display: "block", fontSize: 13, fontWeight: 500, marginBottom: 4 }}>
                  Мин. рейтинг:
                </label>
                <input
                  type="number"
                  min="0"
                  max="5"
                  step="0.1"
                  value={filterMinRating ?? ""}
                  onChange={(e) =>
                    setFilterMinRating(e.target.value ? parseFloat(e.target.value) : undefined)
                  }
                  placeholder="0.0"
                  style={{
                    width: "100%",
                    padding: "6px 8px",
                    borderRadius: 4,
                    border: "1px solid #ccc",
                    fontSize: 14,
                    boxSizing: "border-box",
                  }}
                />
              </div>
            </div>
          )}
        </div>
      )}

      {/* Pagination mode selector */}
      {filteredAndSortedItems.length > ITEMS_PER_PAGE && (
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 16,
            padding: "12px",
            backgroundColor: "#f8f9fa",
            borderRadius: 8,
            flexWrap: "wrap",
            gap: 12,
          }}
        >
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <span style={{ fontSize: 14, fontWeight: 500 }}>Режим:</span>
            <button
              type="button"
              onClick={() => {
                setPaginationMode("pages")
                setCurrentPage(1)
              }}
              style={{
                padding: "6px 12px",
                backgroundColor: paginationMode === "pages" ? "#007bff" : "#e9ecef",
                color: paginationMode === "pages" ? "white" : "#495057",
                border: "none",
                borderRadius: 4,
                cursor: "pointer",
                fontSize: 14,
              }}
            >
              Страницы
            </button>
            <button
              type="button"
              onClick={() => {
                setPaginationMode("load-more")
                setDisplayedCount(ITEMS_PER_PAGE)
              }}
              style={{
                padding: "6px 12px",
                backgroundColor: paginationMode === "load-more" ? "#007bff" : "#e9ecef",
                color: paginationMode === "load-more" ? "white" : "#495057",
                border: "none",
                borderRadius: 4,
                cursor: "pointer",
                fontSize: 14,
              }}
            >
              Загрузить еще
            </button>
          </div>

          {paginationMode === "pages" && (
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <span style={{ fontSize: 14, color: "#666" }}>
                Страница {currentPage} из {totalPages} ({filteredAndSortedItems.length} всего)
              </span>
            </div>
          )}

          {paginationMode === "load-more" && (
            <span style={{ fontSize: 14, color: "#666" }}>
              Показано {displayedCount} из {filteredAndSortedItems.length}
            </span>
          )}
        </div>
      )}

      <div
        className="attractions-grid"
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(5, 1fr)",
          gap: 16,
          flex: 1,
          minHeight: "500px",
        }}
      >
        {displayedItems.map((attraction) => {
          const isPlanned = plannedIds.includes(attraction.id) // 👈 новое

          return (
            <article
              key={attraction.id}
              style={{
                border: "1px solid #e1e1e1",
                borderRadius: 12,
                padding: 16,
                boxShadow: "0 4px 12px rgba(0, 0, 0, 0.08)",
                backgroundColor: "#fff",
                display: "flex",
                flexDirection: "column",
                gap: 12,
                // position: "relative",  // можно убрать, больше не нужно
              }}
            >
              {/* 👇 НОВЫЙ БЛОК С КАРТИНКОЙ */}
              {attraction.image_url && (
                <div
                  style={{
                    width: "100%",
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
                      height: 140,       // единый размер
                      objectFit: "cover",
                      display: "block",
                    }}
                  />
                </div>
              )}

              <div>
                <div
                  style={{
                    fontSize: 12,
                    color: "#6c757d",
                    textTransform: "uppercase",
                    letterSpacing: 0.6,
                  }}
                >
                  #{attraction.id}
                </div>
                <h3 style={{ margin: "4px 0 0", fontSize: 18, lineHeight: 1.4 }}>
                  {attraction.name}
                </h3>
              </div>

              {/* City and Type prominently displayed */}
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 4 }}>
                {attraction.city && (
                  <span
                    style={{
                      backgroundColor: "#e3f2fd",
                      color: "#1976d2",
                      padding: "4px 10px",
                      borderRadius: 12,
                      fontSize: 13,
                      fontWeight: 500,
                    }}
                  >
                    📍 {attraction.city}
                  </span>
                )}
                {attraction.type && (
                  <span
                    style={{
                      backgroundColor: "#f3e5f5",
                      color: "#7b1fa2",
                      padding: "4px 10px",
                      borderRadius: 12,
                      fontSize: 13,
                      fontWeight: 500,
                    }}
                  >
                    🏛️ {attraction.type}
                  </span>
                )}
              </div>

              {/* Rating as stars */}
              {typeof attraction.rating === "number" && (
                <div>
                  <StarRating rating={attraction.rating} />
                </div>
              )}

              {/* Other details */}
              <dl
                style={{
                  margin: 0,
                  display: "grid",
                  gridTemplateColumns: "auto 1fr",
                  rowGap: 6,
                  columnGap: 8,
                  fontSize: 14,
                }}
              >
                {detailFields.map(({ label, key }) => {
                  const value = attraction[key]
                  if (!value) {
                    return null
                  }
                  return (
                    <Fragment key={`${attraction.id}-${String(key)}`}>
                      <dt style={{ fontWeight: 600, color: "#495057" }}>{label}:</dt>
                      <dd style={{ margin: 0, color: "#212529" }}>{value}</dd>
                    </Fragment>
                  )
                })}
              </dl>
              {/* Блок действий: текст + кнопка */}
              <div
                style={{
                  marginTop: "auto",
                  display: "flex",
                  justifyContent: "flex-end",
                  alignItems: "center",
                  gap: 8,
                }}
              >
                {isPlanned && (
                  <span
                    style={{
                      color: "#198754",
                      fontSize: 13,
                      fontWeight: 500,
                    }}
                  >
                    Посещение запланировано!
                  </span>
                )}

                <button
                  type="button"
                  onClick={() => {
                    console.log(
                      isPlanned ? "Cancel planned, id =" : "Planned click, id =",
                      attraction.id
                    )
                    if (isPlanned) {
                      onCancelPlanned(attraction.id)
                    } else {
                      onPlannedClick(attraction.id)
                    }
                  }}
                  style={{
                    padding: "6px 10px",
                    backgroundColor: isPlanned ? "#dc3545" : "#f4a460",
                    color: isPlanned ? "#fff" : "#3c2f2f",
                    border: "none",
                    borderRadius: 6,
                    cursor: "pointer",
                    fontSize: 13,
                    fontWeight: 500,
                    boxShadow: "0 2px 4px rgba(0,0,0,0.15)",
                    whiteSpace: "nowrap",
                  }}
                >
                  {isPlanned ? "Отменить визит" : "Собираюсь посетить"}
                </button>
              </div>
            </article>
          )
        })}
      </div>

      {/* Pagination controls */}
      {items.length > ITEMS_PER_PAGE && (
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            gap: 12,
            marginTop: "auto",
            paddingTop: 24,
            flexWrap: "wrap",
            minHeight: "120px",
          }}
        >
          {paginationMode === "pages" ? (
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: 16,
                alignItems: "center",
                width: "100%",
              }}
            >
              {/* Page numbers */}
              <div
                style={{
                  display: "flex",
                  gap: 8,
                  alignItems: "center",
                  flexWrap: "wrap",
                  justifyContent: "center",
                }}
              >
                <button
                  type="button"
                  onClick={handlePrevious}
                  disabled={!canGoPrevious}
                  style={{
                    padding: "8px 16px",
                    backgroundColor: canGoPrevious ? "#007bff" : "#e9ecef",
                    color: canGoPrevious ? "white" : "#6c757d",
                    border: "none",
                    borderRadius: 4,
                    cursor: canGoPrevious ? "pointer" : "not-allowed",
                    fontSize: 14,
                  }}
                >
                  ←
                </button>

                {getPageNumbers().map((page, index) => {
                  if (page === "...") {
                    return (
                      <span
                        key={`ellipsis-${index}`}
                        style={{
                          padding: "8px 4px",
                          color: "#6c757d",
                          fontSize: 14,
                        }}
                      >
                        ...
                      </span>
                    )
                  }

                  const pageNum = page as number
                  const isActive = pageNum === currentPage

                  return (
                    <button
                      key={pageNum}
                      type="button"
                      onClick={() => handleGoToPage(pageNum)}
                      style={{
                        padding: "8px 12px",
                        backgroundColor: isActive ? "#007bff" : "#fff",
                        color: isActive ? "white" : "#495057",
                        border: isActive ? "none" : "1px solid #dee2e6",
                        borderRadius: 4,
                        cursor: "pointer",
                        fontSize: 14,
                        fontWeight: isActive ? 600 : 400,
                        minWidth: 40,
                      }}
                    >
                      {pageNum}
                    </button>
                  )
                })}

                <button
                  type="button"
                  onClick={handleNext}
                  disabled={!hasMore}
                  style={{
                    padding: "8px 16px",
                    backgroundColor: hasMore ? "#007bff" : "#e9ecef",
                    color: hasMore ? "white" : "#6c757d",
                    border: "none",
                    borderRadius: 4,
                    cursor: hasMore ? "pointer" : "not-allowed",
                    fontSize: 14,
                  }}
                >
                  →
                </button>
              </div>

              {/* Go to page input */}
              <div
                style={{
                  display: "flex",
                  gap: 8,
                  alignItems: "center",
                  fontSize: 14,
                }}
              >
                <span style={{ color: "#495057" }}>Перейти на страницу:</span>
                <input
                  type="number"
                  min={1}
                  max={totalPages}
                  value={currentPage}
                  onChange={(e) => {
                    const value = parseInt(e.target.value)
                    if (!isNaN(value)) {
                      handleGoToPage(value)
                    }
                  }}
                  style={{
                    width: 60,
                    padding: "6px 8px",
                    border: "1px solid #dee2e6",
                    borderRadius: 4,
                    fontSize: 14,
                    textAlign: "center",
                  }}
                />
                <span style={{ color: "#6c757d" }}>из {totalPages}</span>
              </div>
            </div>
          ) : (
            <button
              type="button"
              onClick={handleLoadMore}
              disabled={!hasMore}
              style={{
                padding: "10px 24px",
                backgroundColor: hasMore ? "#198754" : "#e9ecef",
                color: hasMore ? "white" : "#6c757d",
                border: "none",
                borderRadius: 4,
                cursor: hasMore ? "pointer" : "not-allowed",
                fontSize: 16,
                fontWeight: 500,
              }}
            >
              {hasMore ? `Загрузить еще ${Math.min(ITEMS_PER_PAGE, items.length - displayedCount)}` : "Все загружено"}
            </button>
          )}
        </div>
      )}
    </section>
  )
}

