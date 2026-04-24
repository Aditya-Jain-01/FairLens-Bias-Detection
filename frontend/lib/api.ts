// lib/api.ts — All API functions with mock fallback

import {
  JobStatus,
  Results,
  Explanation,
  ThresholdResult,
  UploadCSVResponse,
  UploadModelResponse,
  ConfigureJobResponse,
} from "./types"
import {
  mockResults,
  mockExplanation,
  mockThresholdSeries,
} from "./mockData"

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"
const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK === "true"

/** Returns headers with X-API-Key attached for every authenticated request. */
function getHeaders(extra?: Record<string, string>): Record<string, string> {
  const key = process.env.NEXT_PUBLIC_API_KEY || ""
  return {
    ...(key ? { "X-API-Key": key } : {}),
    ...extra,
  }
}

// ── Upload ──────────────────────────────────────────────────────────────────

export async function uploadCSV(file: File): Promise<UploadCSVResponse> {
  if (USE_MOCK) {
    await delay(800)
    return {
      job_id: "3f7a1b2c-demo",
      columns: [
        "age", "workclass", "fnlwgt", "education", "education_num",
        "marital_status", "occupation", "relationship", "race", "sex",
        "capital_gain", "capital_loss", "hours_per_week", "native_country", "income",
      ],
      row_count: 48842,
    }
  }
  const form = new FormData()
  form.append("file", file)
  const res = await fetch(`${API_BASE}/upload/csv`, { method: "POST", body: form, headers: getHeaders() })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function uploadModel(
  file: File,
  job_id: string
): Promise<UploadModelResponse> {
  if (USE_MOCK) {
    await delay(600)
    return { job_id, model_type: "sklearn_logistic_regression" }
  }
  const form = new FormData()
  form.append("file", file)
  form.append("job_id", job_id)
  const res = await fetch(`${API_BASE}/upload/model`, { method: "POST", body: form, headers: getHeaders() })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

// ── Configure ───────────────────────────────────────────────────────────────

export async function configureJob(
  job_id: string,
  target_column: string,
  protected_attributes: string[],
  positive_outcome_label: number
): Promise<ConfigureJobResponse> {
  if (USE_MOCK) {
    await delay(400)
    return { job_id, status: "queued" }
  }
  const res = await fetch(`${API_BASE}/analyze/configure`, {
    method: "POST",
    headers: getHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({
      job_id,
      target_column,
      protected_attributes,
      positive_outcome_label,
    }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

// ── Status (for SWR polling) ────────────────────────────────────────────────

let mockStage = 0
const MOCK_STAGES: JobStatus[] = [
  { job_id: "demo", stage: "uploading", progress: 10, message: "Uploading data...", error: null },
  { job_id: "demo", stage: "running_inference", progress: 30, message: "Running model inference...", error: null },
  { job_id: "demo", stage: "computing_metrics", progress: 55, message: "Computing fairness metrics...", error: null },
  { job_id: "demo", stage: "generating_explanation", progress: 75, message: "Generating AI explanation...", error: null },
  { job_id: "demo", stage: "generating_report", progress: 90, message: "Building audit report...", error: null },
  { job_id: "demo", stage: "complete", progress: 100, message: "Audit complete!", error: null },
]

export async function pollStatus(job_id: string): Promise<JobStatus> {
  if (USE_MOCK) {
    await delay(600)
    const status = { ...MOCK_STAGES[Math.min(mockStage, MOCK_STAGES.length - 1)], job_id }
    if (mockStage < MOCK_STAGES.length - 1) mockStage++
    return status
  }
  const res = await fetch(`${API_BASE}/status/${job_id}`, { headers: getHeaders() })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export function resetMockStage() {
  mockStage = 0
}

// ── Results ──────────────────────────────────────────────────────────────────

export async function getResults(job_id: string): Promise<Results> {
  if (USE_MOCK) {
    await delay(300)
    return { ...mockResults, job_id }
  }
  const res = await fetch(`${API_BASE}/results/${job_id}`, { headers: getHeaders() })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

// ── Explanation (SSE stream) ─────────────────────────────────────────────────

export function streamExplanation(
  job_id: string,
  onChunk: (text: string) => void,
  onDone: (exp: Explanation) => void,
  onError?: (err: Error) => void
): () => void {
  if (USE_MOCK) {
    const fullText = mockExplanation.plain_english
    let i = 0
    const interval = setInterval(() => {
      if (i < fullText.length) {
        onChunk(fullText.slice(0, i + 3))
        i += 3
      } else {
        clearInterval(interval)
        onDone(mockExplanation)
      }
    }, 30)
    return () => clearInterval(interval)
  }

  let cancelled = false

  const connect = () => {
    if (cancelled) return
    // Issue 4 fix: Use fetch with ReadableStream instead of EventSource
    // P3's /explain endpoint is POST-only SSE — EventSource only supports GET
    fetch(`${API_BASE}/explain`, {
      method: "POST",
      headers: getHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ job_id }),
    })
      .then(async (res) => {
        if (cancelled || !res.body) return

        // Check if response is SSE stream or JSON
        const contentType = res.headers.get("content-type") || ""
        if (contentType.includes("application/json")) {
          // Non-streaming response (mock or cached explanation)
          const data = await res.json()
          if (data.plain_english) {
            onChunk(data.plain_english)
            onDone(data as Explanation)
          }
          return
        }

        // SSE stream parsing
        const reader = res.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ""

        while (true) {
          const { done, value } = await reader.read()
          if (done || cancelled) break
          buffer += decoder.decode(value, { stream: true })

          // Parse SSE lines from buffer
          const lines = buffer.split("\n")
          buffer = lines.pop() || "" // Keep incomplete line in buffer

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue
            try {
              const data = JSON.parse(line.slice(6))
              if (data.chunk) onChunk(data.chunk)
              if (data.done && data.explanation) onDone(data.explanation)
              if (data.error) onError?.(new Error(data.error))
            } catch {
              // Ignore malformed SSE lines
            }
          }
        }
      })
      .catch((err) => {
        if (!cancelled) onError?.(err)
      })
  }

  connect()
  return () => {
    cancelled = true
  }
}

// ── Ask ──────────────────────────────────────────────────────────────────────

export async function askQuestion(
  job_id: string,
  question: string
): Promise<{ answer: string }> {
  if (USE_MOCK) {
    await delay(1200)
    return {
      answer:
        "Based on the audit results, the primary driver of bias in this model is the disparate impact on gender. Women are approved at 62% the rate of men, which falls below the legal 80% threshold. Applying reweighing remediation would bring the model into compliance with only a 1.6% accuracy trade-off.",
    }
  }
  const res = await fetch(`${API_BASE}/ask`, {
    method: "POST",
    headers: getHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ job_id, question }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

// ── Threshold simulator ───────────────────────────────────────────────────────

let thresholdTimer: ReturnType<typeof setTimeout> | null = null

export function getThresholdDebounced(
  job_id: string,
  threshold: number,
  cb: (result: ThresholdResult) => void
): void {
  if (thresholdTimer) clearTimeout(thresholdTimer)
  thresholdTimer = setTimeout(async () => {
    try {
      const result = await getThreshold(job_id, threshold)
      cb(result)
    } catch {}
  }, 150)
}

export async function getThreshold(
  job_id: string,
  threshold: number
): Promise<ThresholdResult> {
  if (USE_MOCK) {
    await delay(100)
    // Interpolate from mock series
    const rounded = Math.round(threshold * 10) / 10
    const nearest = mockThresholdSeries[rounded] || mockThresholdSeries[0.5]
    return {
      ...nearest,
      threshold,
      accuracy: nearest.accuracy + (Math.random() - 0.5) * 0.005,
      demographic_parity_difference:
        nearest.demographic_parity_difference + (Math.random() - 0.5) * 0.005,
    }
  }
  const res = await fetch(
    `${API_BASE}/remediate/threshold?job_id=${job_id}&threshold=${threshold}`,
    { headers: getHeaders() }
  )
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

// ── Report download ───────────────────────────────────────────────────────────

export async function downloadReport(job_id: string): Promise<void> {
  if (USE_MOCK) {
    throw new Error("Mock mode does not support PDF downloads. Use the real API to generate reports.")
  }

  const pendingWindow = window.open("", "_blank", "noopener,noreferrer")
  if (pendingWindow) {
    pendingWindow.document.write(
      "<html><body style='margin:0;font-family:Arial,sans-serif;background:#07111b;color:#dffcf8;display:flex;align-items:center;justify-content:center;min-height:100vh;'>Preparing report...</body></html>"
    )
  }

  try {
    const res = await fetch(`${API_BASE}/report/${job_id}`, { headers: getHeaders() })

    if (!res.ok) {
      const errorText = await res.text()
      throw new Error(`API error: ${res.status} - ${errorText}`)
    }

    const data = await res.json()
    const { download_url } = data
    if (!download_url) {
      throw new Error("No download_url in response")
    }

    let url = download_url
    if (url.startsWith("/")) {
      const baseUrl = API_BASE.replace(/\/api\/v1\/?$/, "")
      url = `${baseUrl}${url}`
    }

    // 2. Fetch the actual PDF bytes WITH the API key
    const pdfRes = await fetch(url, { headers: getHeaders() })
    if (!pdfRes.ok) {
        const errText = await pdfRes.text()
        throw new Error(`Failed to download PDF: ${pdfRes.status} - ${errText}`)
    }

    // 3. Convert to blob and trigger browser download
    const blob = await pdfRes.blob()
    const blobUrl = URL.createObjectURL(blob)

    if (pendingWindow) {
      pendingWindow.location.href = blobUrl
      pendingWindow.focus()
    } else {
      const anchor = document.createElement("a")
      anchor.href = blobUrl
      anchor.download = `fairlens_report_${job_id.slice(0, 8)}.pdf`
      document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
    }

    // Clean up the object URL after navigation
    setTimeout(() => URL.revokeObjectURL(blobUrl), 10000)

  } catch (err) {
    pendingWindow?.close()
    throw err instanceof Error ? err : new Error(String(err))
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function delay(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms))
}
