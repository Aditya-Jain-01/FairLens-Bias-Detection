import React from 'react';
import type { Results } from '@/lib/types';
import { AlertCircle, CheckCircle2 } from 'lucide-react';

export const MetricsGrid = ({ metrics }: { metrics: Results['metrics'] }) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
      {Object.entries(metrics).map(([key, data]) => {
        const passed = data.passed;
        const title = key.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
        
        return (
          <div key={key} className={`glass p-6 rounded-2xl flex flex-col border-l-4 ${passed ? 'border-l-emerald-500' : 'border-l-rose-500'}`}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-slate-700">{title}</h3>
              {passed ? 
                <CheckCircle2 className="w-6 h-6 text-emerald-500" /> : 
                <AlertCircle className="w-6 h-6 text-rose-500" />
              }
            </div>
            
            <div className="flex items-baseline gap-2 mb-2">
              <span className={`text-4xl font-extrabold tracking-tight ${passed ? 'text-emerald-700' : 'text-rose-700'}`}>
                {data.value.toFixed(3)}
              </span>
              <span className="text-sm font-medium text-slate-500">
                / {data.threshold} limits
              </span>
            </div>
            
            <div className="mt-auto pt-4 border-t border-slate-100">
              <p className="text-xs text-slate-500 leading-relaxed font-medium">
                {data.description}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
};
