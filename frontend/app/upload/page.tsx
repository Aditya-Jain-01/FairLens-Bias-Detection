"use client";
import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, ArrowRight } from "lucide-react";
import { DropZone } from "@/components/upload/DropZone";
import { ColumnPicker } from "@/components/upload/ColumnPicker";
import { uploadCSV, uploadModel, configureJob } from "@/lib/api";
import { getJobLabelFromFileName, upsertRecentJob } from "@/lib/recentJobs";

export default function UploadPage() {
  const router = useRouter();

  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [modelFile, setModelFile] = useState<File | null>(null);
  const [columns, setColumns] = useState<string[]>([]);
  const [jobId, setJobId] = useState<string>("");

  const [targetColumn, setTargetColumn] = useState<string>("");
  const [protectedAttributes, setProtectedAttributes] = useState<string[]>([]);

  const [step, setStep] = useState<1 | 2>(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>("");

  const handleCsvUpload = async (file: File) => {
    setCsvFile(file);
    setLoading(true);
    setError("");
    try {
      const res = await uploadCSV(file);
      setJobId(res.job_id);
      setColumns(res.columns);
      upsertRecentJob({
        job_id: res.job_id,
        label: getJobLabelFromFileName(file.name),
        stage: "uploading",
        progress: 5,
        message: "CSV uploaded, waiting for configuration.",
      });
    } catch (e) {
      setError(`Failed to upload CSV: ${(e as Error).message}`);
      setCsvFile(null);
    }
    setLoading(false);
  };

  const handleModelUpload = async (file: File) => {
    if (!jobId) {
      setError("Please upload a CSV dataset first.");
      return;
    }
    setModelFile(file);
    setLoading(true);
    setError("");
    try {
      await uploadModel(file, jobId);
    } catch (e) {
      setError(`Failed to upload model: ${(e as Error).message}`);
      setModelFile(null);
    }
    setLoading(false);
  };

  const submitConfiguration = async () => {
    if (!targetColumn) {
      setError("Please select a target variable.");
      return;
    }
    if (protectedAttributes.length === 0) {
      setError("Please select at least one protected attribute.");
      return;
    }

    setLoading(true);
    try {
      await configureJob(jobId, targetColumn, protectedAttributes, 1);
      upsertRecentJob({
        job_id: jobId,
        label: csvFile ? getJobLabelFromFileName(csvFile.name) : undefined,
        stage: "configuring",
        progress: 10,
        message: "Configuration saved. Audit queued.",
        target_column: targetColumn,
        protected_attributes: protectedAttributes,
      });
      router.push(`/loading/${jobId}`);
    } catch (e) {
      setError(`Failed to start job: ${(e as Error).message}`);
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-6xl animate-fade-in">
      <div className="panel mb-8 overflow-hidden px-6 py-8 sm:px-8">
        <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
          <div>
            <div className="inline-flex rounded-full border border-amber-600/15 bg-amber-500/10 px-4 py-2 text-xs uppercase tracking-[0.26em] text-[#d97706]">
              Configure Audit
            </div>
            <h1 className="mt-5 font-[family-name:var(--font-display)] text-4xl font-bold text-amber-950 sm:text-5xl">
              Upload assets and map your protected features
            </h1>
            <p className="mt-4 max-w-2xl text-lg leading-8 text-amber-900/70">
              The pipeline stays the same. We are improving readability, guidance, and hosted usability while keeping your backend flow intact.
            </p>
          </div>

          <div className="panel-soft p-5">
            <div className="text-xs uppercase tracking-[0.26em] text-amber-900/50">Audit readiness</div>
            <div className="mt-4 grid gap-3">
              {[
                ["Dataset", csvFile?.name || "Required CSV pending"],
                ["Model", modelFile?.name || "Optional artifact"],
                ["Configuration", targetColumn ? "Mapped" : "Not mapped yet"],
              ].map(([label, value]) => (
                <div key={label} className="flex items-center justify-between rounded-2xl border border-amber-600/10 bg-amber-500/5 px-4 py-3">
                  <span className="text-sm text-amber-900/60">{label}</span>
                  <span className="max-w-[60%] truncate text-sm font-medium text-cyan-100">{value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {error && (
        <div className="mb-8 rounded-2xl border border-rose-400/20 bg-rose-500/10 p-4 font-medium text-rose-200">
          {error}
        </div>
      )}

      {step === 1 && (
        <div className="animate-slide-up space-y-8">
          <div className="grid gap-8 md:grid-cols-2">
            <div>
              <h2 className="mb-4 text-xl font-bold text-amber-950">1. Training Data</h2>
              <DropZone
                label="Upload Data (.csv)"
                accept=".csv"
                onFileSelect={handleCsvUpload}
                selectedFileName={csvFile?.name}
              />
            </div>

            <div className={`transition-opacity duration-300 ${!jobId ? "pointer-events-none opacity-50" : "opacity-100"}`}>
              <h2 className="mb-4 text-xl font-bold text-amber-950">2. Model Artifact</h2>
              <DropZone
                label="Upload Model (.pkl / .onnx)"
                accept=".pkl,.onnx"
                onFileSelect={handleModelUpload}
                selectedFileName={modelFile?.name}
              />
            </div>
          </div>

          <div className="panel-soft flex items-center justify-between p-5">
            <div>
              <div className="text-sm font-semibold text-amber-950">Step 1 of 2</div>
              <div className="text-sm text-amber-900/60">Upload a CSV first. Model upload stays optional.</div>
            </div>
            <button
              onClick={() => setStep(2)}
              disabled={!jobId || loading}
              className="btn-primary disabled:cursor-not-allowed disabled:opacity-40"
            >
              {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : "Next Step"}
              {!loading && <ArrowRight className="h-5 w-5" />}
            </button>
          </div>
        </div>
      )}

      {step === 2 && (
        <div className="animate-slide-up">
          <div className="mb-2 flex items-center justify-between">
            <h2 className="text-xl font-bold text-amber-950">Map Variables</h2>
            <button onClick={() => setStep(1)} className="text-sm text-[#d97706]/75 transition hover:text-cyan-100">
              Back to uploads
            </button>
          </div>

          <ColumnPicker
            columns={columns}
            targetColumn={targetColumn}
            setTargetColumn={setTargetColumn}
            protectedAttributes={protectedAttributes}
            setProtectedAttributes={setProtectedAttributes}
          />

          <div className="panel-soft mt-12 flex items-center justify-between gap-4 p-6">
            <div>
              <div className="text-sm font-semibold text-amber-950">Step 2 of 2</div>
              <div className="text-sm text-amber-900/60">Choose one target and at least one protected attribute.</div>
            </div>
            <button
              onClick={submitConfiguration}
              disabled={loading || !targetColumn || protectedAttributes.length === 0}
              className="btn-primary disabled:cursor-not-allowed disabled:opacity-40"
            >
              {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : "Run Full Pipeline Audit"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
