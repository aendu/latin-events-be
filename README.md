# Latin Events Bern

This project collects upcoming latin dance events from [latino.ch](https://www.latino.ch/events?locale=de), [bachata-bern.ch](https://bachata-bern.ch/events/), and [dimelocantando.ch](https://dimelocantando.ch/de-CH/home). It publishes them in a mobile-friendly React table with region, label, and date filters.

## Project structure

- `scripts/crawl_events_latino_ch.py` – crawler for latino.ch (writes `data/events_latino_ch.csv`).
- `scripts/crawl_events_bachata_bern_ch.py` – crawler for bachata-bern.ch (writes `data/events-bachata-bern.csv`).
- `scripts/crawl_events_dimelocantando_ch.py` – crawler for dimelocantando.ch (writes `data/events-dimelocantando.csv`).
- `scripts/crawl_all_events.py` – runs all crawlers and merges their CSV outputs.
- `data/events_latino_ch.csv`, `data/events-bachata-bern.csv`, and `data/events-dimelocantando.csv` – per-site datasets.
- `data/events.csv` – merged dataset produced by `crawl_all_events.py`.
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

Run the master crawler to refresh and merge both sources:

```bash
python3 scripts/crawl_all_events.py
```

The script:

1. Pulls events from latino.ch, bachata-bern.ch, and dimelocantando.ch.
2. Normalises location info and derives the macro-region.
3. Deduplicates by date, time, name, and city.
4. Writes the per-source CSVs, merges them into `data/events.csv`, and copies the merged file to `public/events.csv`.

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
  - **Date** – inclusive ISO start date.
- Each row surfaces the flyer thumbnail (if available), host/location info, quick links to the original event page, and a list of labels.
- The reset button restores all filters to their default state.

## Notes

- When fiat city text does not include a postcode, the crawler uses common city keywords to fall back to the best region.
- The `labels` column stores a pipe-delimited list; the frontend automatically splits it into badge elements.
