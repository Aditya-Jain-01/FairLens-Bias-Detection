"use client";
import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { DropZone } from '@/components/upload/DropZone';
import { ColumnPicker } from '@/components/upload/ColumnPicker';
import { uploadCSV, uploadModel, configureJob } from '@/lib/api';
import { Loader2, ArrowRight } from 'lucide-react';

export default function UploadPage() {
  const router = useRouter();
  
  // Form state
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [modelFile, setModelFile] = useState<File | null>(null);
  const [columns, setColumns] = useState<string[]>([]);
  const [jobId, setJobId] = useState<string>('');
  
  // Selection state
  const [targetColumn, setTargetColumn] = useState<string>('');
  const [protectedAttributes, setProtectedAttributes] = useState<string[]>([]);
  
  // View state
  const [step, setStep] = useState<1 | 2>(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');

  const handleCsvUpload = async (file: File) => {
    setCsvFile(file);
    setLoading(true);
    setError('');
    try {
      const res = await uploadCSV(file);
      setJobId(res.job_id);
      setColumns(res.columns);
    } catch (e: any) {
      setError(`Failed to upload CSV: ${e.message}`);
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
    setError('');
    try {
      await uploadModel(file, jobId);
    } catch (e: any) {
      setError(`Failed to upload Model: ${e.message}`);
      setModelFile(null);
    }
    setLoading(false);
  };

  const submitConfiguration = async () => {
    if (!targetColumn) return setError("Please select a target variable.");
    if (protectedAttributes.length === 0) return setError("Please select at least one protected attribute.");
    
    setLoading(true);
    try {
      await configureJob(
        jobId,
        targetColumn,
        protectedAttributes,
        1
      );
      // Redirect to loading status poller
      router.push(`/loading/${jobId}`);
    } catch (e: any) {
      setError(`Failed to start job: ${e.message}`);
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto pt-8 animate-fade-in">
      <div className="mb-10">
        <h1 className="text-3xl font-extrabold text-slate-900 mb-2">Configure Bias Audit</h1>
        <p className="text-slate-500 text-lg">Define your inputs to generate the FairLens evaluation pipeline.</p>
      </div>

      {error && (
        <div className="bg-rose-50 text-rose-700 p-4 rounded-xl border border-rose-200 mb-8 font-medium">
          {error}
        </div>
      )}

      {step === 1 && (
        <div className="space-y-8 animate-slide-up">
          <div className="grid md:grid-cols-2 gap-8">
            <div>
              <h2 className="text-xl font-bold mb-4">1. Training Data (Required)</h2>
              <DropZone 
                label="Upload Data (.csv)" 
                accept=".csv" 
                onFileSelect={handleCsvUpload} 
                selectedFileName={csvFile?.name}
              />
            </div>
            
            <div className={`transition-opacity duration-300 ${!jobId ? 'opacity-50 pointer-events-none' : 'opacity-100'}`}>
              <h2 className="text-xl font-bold mb-4">2. Model Artifact (Optional)</h2>
              <DropZone 
                label="Upload Model (.pkl / .onnx)" 
                accept=".pkl,.onnx" 
                onFileSelect={handleModelUpload}
                selectedFileName={modelFile?.name}
              />
            </div>
          </div>

          <div className="flex justify-end pt-4">
            <button 
              onClick={() => setStep(2)}
              disabled={!jobId || loading}
              className="flex items-center gap-2 px-8 py-3 bg-slate-900 hover:bg-slate-800 disabled:bg-slate-300 text-white font-medium rounded-xl transition-all shadow-md"
            >
              {loading ? <Loader2 className="w-5 h-5 animate-spin"/> : 'Next Step'}
              {!loading && <ArrowRight className="w-5 h-5"/>}
            </button>
          </div>
        </div>
      )}

      {step === 2 && (
        <div className="animate-slide-up">
           <div className="flex items-center justify-between mb-2">
             <h2 className="text-xl font-bold">Map Variables</h2>
             <button onClick={() => setStep(1)} className="text-sm text-slate-500 hover:text-slate-800 underline">Back to uploads</button>
           </div>
           
           <ColumnPicker 
             columns={columns}
             targetColumn={targetColumn}
             setTargetColumn={setTargetColumn}
             protectedAttributes={protectedAttributes}
             setProtectedAttributes={setProtectedAttributes}
           />

          <div className="flex justify-end mt-12 bg-white/50 p-6 rounded-2xl border border-slate-200 shadow-sm">
            <button 
              onClick={submitConfiguration}
              disabled={loading || !targetColumn || protectedAttributes.length === 0}
              className="flex items-center gap-2 px-10 py-4 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 text-white text-lg font-bold rounded-xl transition-all shadow-lg"
            >
              {loading ? <Loader2 className="w-5 h-5 animate-spin"/> : 'Run Full Pipeline Audit'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
