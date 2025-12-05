import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import Papa from 'papaparse'
import arrowDownIcon from './assets/icons/basic_magnifier.svg'
import arrowUpIcon from './assets/icons/arrows_circle_up.svg'
import logo from './assets/logo.webp'
import './App.css'

const SHORT_DATE = new Intl.DateTimeFormat('de-CH', {
  weekday: 'short',
  day: '2-digit',
  month: 'short',
})

const FULL_DATE = new Intl.DateTimeFormat('de-CH', {
  dateStyle: 'full',
})

const TODAY = (() => {
  const now = new Date()
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
})()

const INITIAL_VISIBLE_DAYS = 14
const EVENTS_CSV_URL =
  (typeof window !== 'undefined' && window.location.hostname === 'localhost')
    ? '/events.csv'
    : 'https://raw.githubusercontent.com/aendu/latin-events-be/refs/heads/main/public/events.csv'

const INITIAL_FILTERS = {
  region: 'Region Bern',
  label: 'ohne-kurse',
  style: 'all',
  startDate: TODAY,
}

const STYLE_LABELS = {
  S: 'Salsa',
  B: 'Bachata',
  K: 'Kizomba',
  Z: 'Zouk',
}

function normalizeRow(row) {
  if (!row.date) {
    return null
  }
  const labels = row.labels
    ? row.labels
        .split('|')
        .map((label) => label.trim())
        .filter(Boolean)
    : []
  const styles = row.style
    ? row.style
        .split('|')
        .map((style) => style.trim())
        .filter(Boolean)
    : []
  const dateObj = new Date(`${row.date}T00:00:00`)
  return {
    date: row.date,
    dateObj: Number.isNaN(dateObj.valueOf()) ? null : dateObj,
    time: row.time || '',
    name: row.name || '',
    flyer: row.flyer || '',
    url: row.url || '',
    host: row.host || '',
    city: row.city || '',
    region: row.region || '',
    source: row.source || '',
    labels,
    styles,
  }
}

function App() {
  const [events, setEvents] = useState([])
  const [filters, setFilters] = useState(INITIAL_FILTERS)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [filtersOpen, setFiltersOpen] = useState(true)
  const [showFloatingToggle, setShowFloatingToggle] = useState(false)
  const [visibleSpanDays, setVisibleSpanDays] = useState(INITIAL_VISIBLE_DAYS)
  const filtersOpenRef = useRef(true)
  const autoCollapseRef = useRef(true);
  const loadMoreRef = useRef(null)

  const loadCsvEvents = useCallback(
    ({ cacheBust = '', silent = false } = {}) => {
      if (!silent) {
        setLoading(true)
      }
      setError('')
      const csvUrl = cacheBust ? `${EVENTS_CSV_URL}?v=${cacheBust}` : EVENTS_CSV_URL
      Papa.parse(csvUrl, {
        download: true,
        header: true,
        skipEmptyLines: true,
        complete: (results) => {
          const parsed = results.data.map(normalizeRow).filter((row) => row && row.dateObj)
          parsed.sort((a, b) => {
            if (!a.dateObj || !b.dateObj) return 0
            if (a.dateObj.valueOf() === b.dateObj.valueOf()) {
              return a.time.localeCompare(b.time)
            }
            return a.dateObj.valueOf() - b.dateObj.valueOf()
          })
          setEvents(parsed)
          setLoading(false)
        },
        error: (err) => {
          setError('Die Eventdaten konnten nicht geladen werden.')
          console.error(err)
          setLoading(false)
        },
      })
    },
    []
  )

  useEffect(() => {
    loadCsvEvents()
  }, [loadCsvEvents])

  const regions = useMemo(() => {
    const list = Array.from(new Set(events.map((event) => event.region).filter(Boolean)))
    return list.sort((a, b) => a.localeCompare(b))
  }, [events])

  const labels = useMemo(() => {
    const set = new Set()
    events.forEach((event) => event.labels.forEach((eventType) => set.add(eventType)))
    return Array.from(set).sort((a, b) => a.localeCompare(b))
  }, [events])

  const styles = useMemo(() => {
    const set = new Set()
    events.forEach((event) => event.styles.forEach((style) => set.add(style)))
    return Array.from(set).sort((a, b) => {
      const labelA = STYLE_LABELS[a] || a
      const labelB = STYLE_LABELS[b] || b
      return labelA.localeCompare(labelB)
    })
  }, [events])

  useEffect(() => {
    const handleScroll = () => {
      const scrolled = window.scrollY
      if (filtersOpenRef.current && scrolled > 10) {
        if (autoCollapseRef.current) {
          setFiltersOpen(false)
        }
      }
      setShowFloatingToggle(scrolled > 300)
    }
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  useEffect(() => {
    setVisibleSpanDays(INITIAL_VISIBLE_DAYS)
  }, [filters.startDate, filters.region, filters.label, filters.style])

  const filteredEvents = useMemo(() => {
    if (!events.length) {
      return []
    }
    const start = filters.startDate ? new Date(`${filters.startDate}T00:00:00`) : null

    return events.filter((event) => {
      if (filters.region !== 'all' && event.region !== filters.region) {
        return false
      }
      if (filters.style !== 'all') {
        if (!event.styles.includes(filters.style)) {
          return false
        }
      }
      if (filters.label === 'ohne-kurse') {
        const hasEventTypes = event.labels.length > 0
        const onlyKurs = hasEventTypes && event.labels.every((eventType) => eventType === 'kurs')
        const onlyShopping = hasEventTypes && event.labels.every((eventType) => eventType === 'shopping')
        if (onlyKurs || onlyShopping) {
          return false
        }
      } else if (filters.label !== 'all' && !event.labels.includes(filters.label)) {
        return false
      }
      if (start && (!event.dateObj || event.dateObj < start)) {
        return false
      }
      return true
    })
  }, [events, filters])

  const visibleWindowEnd = useMemo(() => {
    if (!filters.startDate) {
      return null
    }
    const startDate = new Date(`${filters.startDate}T00:00:00`)
    if (Number.isNaN(startDate.valueOf())) {
      return null
    }
    const endDate = new Date(startDate)
    endDate.setDate(startDate.getDate() + visibleSpanDays - 1)
    return endDate
  }, [filters.startDate, visibleSpanDays])

  const visibleEvents = useMemo(() => {
    if (!filteredEvents.length) {
      return []
    }
    if (!visibleWindowEnd) {
      return filteredEvents
    }
    return filteredEvents.filter((event) => event.dateObj && event.dateObj <= visibleWindowEnd)
  }, [filteredEvents, visibleWindowEnd])

  const hasMoreEvents = useMemo(
    () => visibleEvents.length < filteredEvents.length,
    [visibleEvents.length, filteredEvents.length]
  )

  useEffect(() => {
    if (!loadMoreRef.current) {
      return undefined
    }
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting && hasMoreEvents) {
            setVisibleSpanDays((prev) => prev + INITIAL_VISIBLE_DAYS)
          }
        })
      },
      { rootMargin: '200px' }
    )
    const node = loadMoreRef.current
    observer.observe(node)
    return () => observer.unobserve(node)
  }, [hasMoreEvents])

  const groupedEvents = useMemo(() => {
    const groups = []
    let currentGroup = null
    visibleEvents.forEach((event) => {
      if (!currentGroup || currentGroup.date !== event.date) {
        currentGroup = { date: event.date, events: [] }
        groups.push(currentGroup)
      }
      currentGroup.events.push(event)
    })
    return groups
  }, [visibleEvents])

  const handleFilterChange = (field, value) => {
    setFilters((prev) => ({
      ...prev,
      [field]: value,
    }))
  }

  const formatDate = (value) => {
    const dateObj = value instanceof Date ? value : new Date(`${value}T00:00:00`)
    return SHORT_DATE.format(dateObj)
  }

  const formatFullDate = (value) => {
    const dateObj = value instanceof Date ? value : new Date(`${value}T00:00:00`)
    return FULL_DATE.format(dateObj)
  }

  const handleFloatingToggle = () => {
    autoCollapseRef.current = false;
    window.scrollTo({ top: 0, behavior: 'smooth' })
    setFiltersOpen(true)
  }

  const showFloatingButton = showFloatingToggle && !filtersOpen
  const toggleIcon = filtersOpen ? arrowUpIcon : arrowDownIcon
  const totalCount = events.length
  const visibleCount = visibleEvents.length
  const filteredCount = filteredEvents.length
  const resultsLabel = `${filteredCount}/${totalCount} Events` // hasMoreEvents ? `${filteredCount}/${totalCount} Events` : `${visibleCount} Events`

  return (
    <div className="app-shell">
      <div className={`sticky-panel ${filtersOpen ? 'is-open' : 'is-collapsed'}`}>
        <header className="page-header">
          <div className="brand">
            <img src={logo} alt="Latin Events Switzerland" className="brand-logo" />
            <div className="brand-text">
              <p className="eyebrow">Latin Events Switzerland</p>
            </div>
          </div>
          <div className="header-actions">
            <button
              type="button"
              className="filters-toggle"
              onClick={() => { 
                autoCollapseRef.current = filtersOpen;
                setFiltersOpen((prev) => !prev); 
              }}
            >
              <img src={toggleIcon} alt="" aria-hidden="true" className="icon" />
            </button>
          </div>
        </header>

        <section
          className={`filters-card ${filtersOpen ? 'is-open' : 'is-collapsed'}`}
        >
          <div className="filter-group">
            <label htmlFor="region-filter">Region</label>
            <select
              id="region-filter"
              value={filters.region}
              onChange={(event) => handleFilterChange('region', event.target.value)}
            >
              <option value="all">Alle Regionen</option>
              {regions.map((region) => (
                <option key={region} value={region}>
                  {region}
                </option>
              ))}
            </select>
          </div>

          <div className="filter-group">
            <label htmlFor="label-filter">Event-Typ</label>
            <select
              id="label-filter"
              value={filters.label}
              onChange={(event) => handleFilterChange('label', event.target.value)}
            >
              <option value="all">Alle</option>
              <option value="ohne-kurse">ohne Kurse</option>
              {labels.map((label) => (
                <option key={label} value={label}>
                  {label}
                </option>
              ))}
            </select>
          </div>

          <div className="filter-group">
            <label htmlFor="style-filter">Tanzstil</label>
            <select
              id="style-filter"
              value={filters.style}
              onChange={(event) => handleFilterChange('style', event.target.value)}
            >
              <option value="all">Alle Tanzstile</option>
              {styles.map((styleCode) => (
                <option key={styleCode} value={styleCode}>
                  {STYLE_LABELS[styleCode] || styleCode}
                </option>
              ))}
            </select>
          </div>

          <div className="filter-group">
            <label htmlFor="start-date">Datum</label>
            <input
              type="date"
              id="start-date"
              value={filters.startDate}
              onChange={(event) => handleFilterChange('startDate', event.target.value)}
            />
          </div>
        </section>
        
        <div className="hscroll">
            <div className="results-meta">
              <span>{resultsLabel}</span>
              {filters.region !== 'all' && (
                <span className="active-filter">
                  Region: {filters.region}
                  <button
                    type="button"
                    className="chip-close"
                    onClick={() => handleFilterChange('region', 'all')}
                    aria-label="Region Filter entfernen"
                  >
                    ×
                  </button>
                </span>
              )}
              {filters.label !== 'all' && (
                <span className="active-filter">
                  Event-Typ: {filters.label === 'ohne-kurse' ? 'ohne Kurse' : filters.label}
                  <button
                    type="button"
                    className="chip-close"
                    onClick={() => handleFilterChange('label', 'all')}
                    aria-label="Event-Typ Filter entfernen"
                  >
                    ×
                  </button>
                </span>
              )}
              {filters.style !== 'all' && (
                <span className="active-filter">
                  Tanzstil: {STYLE_LABELS[filters.style] || filters.style}
                  <button
                    type="button"
                    className="chip-close"
                    onClick={() => handleFilterChange('style', 'all')}
                    aria-label="Tanzstil Filter entfernen"
                  >
                    ×
                  </button>
                </span>
              )}
            </div>
          </div>
      </div>

      {loading && (
        <div className="state-message" role="status">
          Events werden geladen…
        </div>
      )}

      {error && (
        <div className="state-message error" role="alert">
          {error}
        </div>
      )}

      <div className="separator"></div>

      {!loading && !error && (
        <>


          <div className="table-wrapper-desktop">
            <table className="events-table">
              <thead>
                <tr>
                  <th>Datum</th>
                  <th>Event</th>
                  <th>Ort</th>
                  <th>Event-Typ</th>
                </tr>
              </thead>
              <tbody>
                {visibleEvents.map((event) => {
                  const shortDate = formatDate(event.dateObj || event.date)
                  return (
                    <tr key={`${event.date}-${event.time}-${event.name}-${event.city}`}>
                      <td>
                        <span className="date-short">{shortDate}</span>
                        <span className="time-inline">{event.time || '—'}</span>
                      </td>
                      <td>
                        <div className="event-cell">
                          {event.flyer ? (
                              <a href={event.url} target="_blank" rel="noreferrer" className="flyer-thumb-link">
                                <img
                                  src={event.flyer}
                                  alt={`Flyer für ${event.name}`}
                                  className="flyer-thumb"
                                  loading="lazy"
                                />
                              </a>
                            ) : (
                              <div className="flyer-thumb placeholder" aria-hidden="true">
                                ✦
                              </div>
                            )}
                            <div>
                            <a href={event.url} target="_blank" rel="noreferrer" className="event-name">
                              {event.name}
                            </a>
                            {event.host && <p className="host">{event.host}</p>}
                            {event.source && <p className="source-note">Provided by {event.source}</p>}
                          </div>
                        </div>
                      </td>
                      <td>
                        <p className="city">{event.city || '—'}</p>
                      </td>
                      <td>
                        <div className="labels-list">
                          {event.labels.length ? (
                            event.labels.map((eventType) => (
                              <span className="label-chip" key={`${event.name}-${eventType}`}>
                                {eventType}
                              </span>
                            ))
                          ) : (
                            <span className="label-chip muted">k.A.</span>
                          )}
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          <div className="events-list-mobile">
            {groupedEvents.map((group) => {
              const headerLabel = formatFullDate(group.date)
              return (
                <section className="mobile-day-section" key={group.date}>
                  <div className="mobile-day-header">{headerLabel}</div>
                  {group.events.map((event) => {
                    const shortDate = formatDate(event.dateObj || event.date)
                    return (
                      <article
                        className="event-card"
                        key={`mobile-${event.date}-${event.time}-${event.name}-${event.city}`}
                      >
                        <div className="event-card__body row">
                          {event.flyer ? (
                            <a href={event.url} target="_blank" rel="noreferrer" className="flyer-thumb-link large">
                              <img
                                src={event.flyer}
                                alt={`Flyer für ${event.name}`}
                                className="flyer-thumb"
                                loading="lazy"
                              />
                            </a>
                          ) : (
                            <div className="flyer-thumb placeholder large" aria-hidden="true">
                              ✦
                            </div>
                          )}
                          <div className="event-card__content">
                            <div className="event-card__meta-line">
                              <span className="date-short">{shortDate}</span>
                              <span className="time-inline">{event.time || '—'}</span>
                            </div>
                            <p className="city subdued">{event.city || '—'}</p>
                            <a href={event.url} target="_blank" rel="noreferrer" className="event-name">
                              {event.name}
                            </a>
                            {event.host && <p className="host subtle-link">{event.host}</p>}
                            {event.source && (
                              <p className="source-note">
                                Provided by {event.source}
                              </p>
                            )}
                          </div>
                          <div className="event-card__label-pill">
                            {event.labels.length ? (
                              event.labels.map((eventType) => (
                                <span className="label-chip" key={`${event.name}-mobile-${eventType}`}>
                                  {eventType}
                                </span>
                              ))
                            ) : (
                              <span className="label-chip muted">k.A.</span>
                            )}
                          </div>
                        </div>
                      </article>
                    )
                  })}
                </section>
              )
            })}
          </div>

          {!visibleEvents.length && (
            <div className="state-message" role="status">
              Keine Events entsprechen den aktuellen Filtern.
            </div>
          )}
        </>
      )}

      <div ref={loadMoreRef} className="load-more-sentinel" aria-hidden="true" />

      <button
        type="button"
        className={`floating-filter-button ${showFloatingButton ? 'is-visible' : ''}`}
        onClick={handleFloatingToggle}
        aria-label="Filter anzeigen"
      >
        Filter
      </button>
    </div>
  )
}

export default App
