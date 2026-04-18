"use client";
import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { pollStatus } from '@/lib/api';
import { JobStatus } from '@/lib/types';
import { CheckCircle2, CircleDashed, Loader2 } from 'lucide-react';

const STEPS = [
  { id: 'configuring', label: 'Saving Configuration' },
  { id: 'running_inference', label: 'Running Model Inference' },
  { id: 'computing_metrics', label: 'Computing Fairness Metrics' },
  { id: 'generating_explanation', label: 'Generating AI Report' },
  { id: 'generating_report', label: 'Finalizing PDF' },
  { id: 'complete', label: 'Audit Complete' },
];

export default function LoadingPage({ params }: { params: { job_id: string } }) {
  const router = useRouter();
  const [status, setStatus] = useState<JobStatus | null>(null);

  useEffect(() => {
    let timeout: NodeJS.Timeout;
    
    const pollStatusFn = async () => {
      try {
        const currentStatus = await pollStatus(params.job_id);
        setStatus(currentStatus);
        
        // Once the AI is generating explanation or it is complete, the dashboard can safely be loaded
        // because the dashboard handles SSE streaming intrinsically!
        if (['generating_explanation', 'generating_report', 'complete'].includes(currentStatus.stage)) {
           setTimeout(() => {
              router.push(`/results/${params.job_id}`);
           }, 1500); // Tiny artificial delay for UX feel
           return;
        }

        if (currentStatus.error) {
           return; // Stop polling on error
        }

        timeout = setTimeout(pollStatusFn, 1500);
      } catch (err) {
        console.error(err);
        timeout = setTimeout(pollStatusFn, 3000);
      }
    };
    
    pollStatusFn();
    return () => clearTimeout(timeout);
  }, [params.job_id, router]);

  if (status?.error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] animate-fade-in">
        <div className="bg-rose-50 text-rose-700 p-8 rounded-2xl max-w-lg border border-rose-200 shadow-lg text-center">
          <h2 className="text-2xl font-bold mb-2">Audit Failed</h2>
          <p>{status.error || status.message}</p>
          <button onClick={() => router.push('/upload')} className="mt-6 px-6 py-2 bg-rose-600 text-white rounded-lg">Try Again</button>
        </div>
      </div>
    );
  }

  const currentStepIndex = STEPS.findIndex(s => s.id === status?.stage);

  return (
    <div className="flex flex-col items-center justify-center min-h-[70vh] animate-fade-in">
      <div className="glass p-12 rounded-3xl max-w-xl w-full shadow-2xl relative overflow-hidden">
        
        <div className="absolute top-0 left-0 w-full h-1 bg-slate-100">
           <div 
             className="h-full bg-gradient-to-r from-indigo-500 to-purple-600 transition-all duration-500" 
             style={{ width: `${status?.progress || 0}%` }}
           />
        </div>

        <div className="text-center mb-10">
          <div className="relative inline-block mb-4">
            <div className="absolute inset-0 bg-indigo-500 blur-xl opacity-30 rounded-full animate-pulse"></div>
            <div className="w-16 h-16 bg-white rounded-2xl flex items-center justify-center relative shadow-sm border border-indigo-100">
              <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
            </div>
          </div>
          <h1 className="text-2xl font-bold text-slate-900">Processing Audit</h1>
          <p className="text-slate-500 text-sm mt-2">{status?.message || "Initializing pipeline..."}</p>
        </div>

        <div className="space-y-6 pl-4">
          {STEPS.map((step, idx) => {
            const isCompleted = currentStepIndex > idx;
            const isCurrent = currentStepIndex === idx;
            
            return (
              <div key={step.id} className={`flex items-center gap-4 transition-all duration-300 ${isCurrent ? 'opacity-100 scale-105 transform origin-left' : isCompleted ? 'opacity-50' : 'opacity-30'}`}>
                {isCompleted ? (
                   <CheckCircle2 className="w-6 h-6 text-emerald-500 shrink-0" />
                ) : isCurrent ? (
                   <Loader2 className="w-6 h-6 text-indigo-500 animate-spin shrink-0" />
                ) : (
                   <CircleDashed className="w-6 h-6 text-slate-400 shrink-0" />
                )}
                <span className={`font-medium ${isCurrent ? 'text-indigo-900 font-bold' : 'text-slate-600'}`}>
                   {step.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
