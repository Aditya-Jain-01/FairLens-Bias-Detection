# FairLens Frontend — Person 4

AI-powered bias detection dashboard built with Next.js 14, Tailwind CSS, and Recharts.

---

## Folder Structure

```
frontend/
├── app/
│   ├── layout.tsx                    ← Shared nav + global layout
│   ├── globals.css                   ← Tailwind base + custom animations
│   ├── page.tsx                      ← Landing page (CTA + Try demo)
│   ├── upload/
│   │   └── page.tsx                  ← Step 1 (drag-drop) + Step 2 (column picker)
│   ├── loading/[job_id]/
│   │   └── page.tsx                  ← Animated step list + SWR polling
│   └── results/[job_id]/
│       └── page.tsx                  ← Full dashboard (all 9 deliverables)
│
├── components/
│   ├── upload/
│   │   ├── DropZone.tsx              ← Drag-drop for CSV + model files
│   │   └── ColumnPicker.tsx          ← Target + protected attribute selector
│   ├── dashboard/
│   │   ├── FairnessScoreCard.tsx     ← Big score + severity badge + dataset info
│   │   ├── MetricsGrid.tsx           ← 4 metric cards (pass/fail coloring)
│   │   ├── PerGroupChart.tsx         ← Grouped bar chart per protected attribute
│   │   ├── ShapChart.tsx             ← Horizontal bar SHAP feature importance
│   │   ├── GeminiPanel.tsx           ← SSE streaming text + findings + Q&A
│   │   ├── ThresholdSimulator.tsx    ← Live slider + dual-line Recharts chart
│   │   └── RemediationComparison.tsx ← Before/after metrics table
│   └── shared/
│       ├── StatusBadge.tsx           ← Severity pill (high/medium/low/none)
│       └── DownloadButton.tsx        ← PDF download trigger
│
├── lib/
│   ├── types.ts                      ← All TypeScript interfaces (matches CONTRACT.md)
│   ├── mockData.ts                   ← Mock results + explanation + threshold series
│   └── api.ts                        ← All API calls with mock fallback
│
├── .env.local.example                ← Copy to .env.local and configure
├── package.json
├── tsconfig.json
├── tailwind.config.ts
├── next.config.js
└── postcss.config.js
```

---

## Prerequisites

- Node.js 18+ (required by Next.js 14)
- npm or yarn

---

## Setup & Run (Step by Step)

### 1. Install dependencies

```bash
cd frontend
npm install
```

### 2. Configure environment

```bash
cp .env.local.example .env.local
```

The default `.env.local` starts in **mock mode** — no backend needed:

```env
NEXT_PUBLIC_USE_MOCK=true
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

### 3. Start the dev server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

---

## Testing Each Feature in Mock Mode

| Feature | How to test |
|---------|-------------|
| Landing page | Visit `http://localhost:3000` |
| Try demo button | Click "Try demo" → goes to loading → goes to results |
| Upload flow | Click "Start audit" → drag any CSV file → pick columns → run audit |
| Loading animation | Auto-advances through 5 stages every ~2s in mock mode |
| Dashboard | All 9 components visible at `/results/demo` |
| Gemini streaming | Text types out automatically on results page |
| Ask a question | Type in GeminiPanel input and press Ask |
| Threshold simulator | Move the slider — chart updates with debounced API call |
| PDF download | Shows alert in mock mode (expected) |

---

## Integration Day (switching to real API)

When Person 1 gives you the Cloud Run URL:

```env
# .env.local
NEXT_PUBLIC_USE_MOCK=false
NEXT_PUBLIC_API_URL=https://fairlens-api-xxxx-uc.a.run.app/api/v1
```

Then restart `npm run dev`. Every API call in `lib/api.ts` will now hit the real backend.

**Integration checklist:**
- [ ] Person 1: `/upload/csv`, `/upload/model`, `/analyze/configure`, `/status/{job_id}`
- [ ] Person 2: `/results/{job_id}`, `/remediate/threshold`, `/remediate/reweigh`
- [ ] Person 3: `/explain` (SSE stream), `/ask`, `/report/{job_id}`

---

## Build for Production (Vercel)

```bash
npm run build
npm run start
```

Or deploy to Vercel:

```bash
npx vercel --prod
```

Set the following environment variables in Vercel dashboard:
- `NEXT_PUBLIC_USE_MOCK=false`
- `NEXT_PUBLIC_API_URL=<Person 1's Cloud Run URL>`

---

## Type Checking

```bash
npm run type-check
```

---

## API Contract Reference

All TypeScript types in `lib/types.ts` exactly match the schemas in `CONTRACT.md`.

| Type | Source |
|------|--------|
| `JobStatus` | `CONTRACT.md` section 3 |
| `Results` | `CONTRACT.md` section 4 |
| `Explanation` | `CONTRACT.md` section 5 |
| API routes | `CONTRACT.md` section 6 |

---

## Troubleshooting

**`Module not found: react-dropzone`**
```bash
npm install react-dropzone
```

**`Module not found: recharts`**
```bash
npm install recharts
```

**`Module not found: swr`**
```bash
npm install swr
```

**Hydration errors on loading page**
Make sure SWR is only used inside `"use client"` components (all pages that use SWR already have this directive).

**Charts not rendering**
All Recharts charts use `ResponsiveContainer` — make sure the parent div has a defined height.
