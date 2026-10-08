# GraphIntel Frontend

Next.js 14 executive research interface for the GraphIntel Market Intelligence platform.

## Technologies
* **Next.js 14 (App Router)**
* **React 18**
* **TypeScript**
* **Tailwind CSS**
* **Lucide Icons**

## Local Setup

```bash
# 1. Install dependencies
npm install

# 2. Start Next.js development server
npm run dev
```

Visit [http://localhost:3000](http://localhost:3000) in your browser.

## Key Routes
* `/` — Landing page with architecture highlights
* `/login` & `/register` — Authentication pages
* `/dashboard` — Market intelligence metric cards and recent filings
* `/documents` — Document manager with drag-and-drop file ingestion
* `/documents/[id]` — Chunk inspector displaying token counts and parsed text
* `/chat` — Research assistant with real citations and latency telemetry

## Production Build

```bash
npm run build
npm run start
```
