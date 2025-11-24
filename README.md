# Latin Events Bern

This project collects upcoming latin dance events from [latino.ch](https://www.latino.ch/events?locale=de) and publishes them in a mobile-friendly React table with region, label and date filters.

## Project structure

- `scripts/crawl_events.py` – crawler that loads at least one month of events via the infinite scroll endpoint and writes them to CSV.
- `data/events.csv` – source of truth for the dataset (also copied to `public/events.csv` for the frontend).
- `public/events.csv` – static asset that the UI fetches at runtime.
- `src` – React app created with Vite.

## Requirements

- Node.js 20+
- npm 10+
- Python 3.9+ with `pip`

Install the JavaScript dependencies:

```bash
npm install
```

Install the Python scraper dependencies:

```bash
python3 -m pip install -r requirements.txt
```

## Updating the data

Run the crawler to refresh the CSV with at least 30 days of events:

```bash
python3 scripts/crawl_events.py
```

The script:

1. Mimics the browser infinite-scroll requests (including the XHR headers).
2. Parses single and clustered event rows.
3. Normalises the location info and derives the requested macro-region.
4. Writes the result to `data/events.csv` and copies the file to `public/events.csv`.

## Developing the frontend

Start the dev server:

```bash
npm run dev
```

Build a production bundle:

```bash
npm run build
```

## UI behavior

- The dataset is displayed in a responsive table that falls back to horizontal scroll on narrow screens.
- Filters:
  - **Region** – matches the derived macro-region.
  - **Label** – matches tag values such as `kurs`, `party`, `show`, `live-music`.
  - **Date range** – inclusive start/end ISO dates.
- Each row surfaces the flyer thumbnail (if available), host/location info, quick links to the original event page, and a list of labels.
- The reset button restores all filters to their default state.

## Notes

- When fiat city text does not include a postcode, the crawler uses common city keywords to fall back to the best region.
- The `labels` column stores a pipe-delimited list; the frontend automatically splits it into badge elements.
