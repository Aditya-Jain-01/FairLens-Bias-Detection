"use client";
import React from 'react';
import { Target, Users } from 'lucide-react';

interface ColumnPickerProps {
  columns: string[];
  targetColumn: string;
  setTargetColumn: (col: string) => void;
  protectedAttributes: string[];
  setProtectedAttributes: (cols: string[]) => void;
}

export const ColumnPicker = ({ columns, targetColumn, setTargetColumn, protectedAttributes, setProtectedAttributes }: ColumnPickerProps) => {
  
  const toggleProtected = (col: string) => {
    if (protectedAttributes.includes(col)) {
      setProtectedAttributes(protectedAttributes.filter(c => c !== col));
    } else {
      setProtectedAttributes([...protectedAttributes, col]);
    }
  };

  return (
    <div className="grid md:grid-cols-2 gap-8 w-full animate-slide-up mt-8">
      {/* Target Column Selection */}
      <div className="glass p-6 rounded-2xl">
        <div className="flex items-center gap-2 mb-4">
          <div className="p-2 bg-indigo-100 text-indigo-600 rounded-lg">
            <Target className="w-5 h-5" />
          </div>
          <h3 className="text-lg font-bold">1. Target Variable</h3>
        </div>
        <p className="text-sm text-slate-500 mb-4">Select the dependent variable your model is predicting (e.g., "loan_approved").</p>
        <div className="flex flex-wrap gap-2">
          {columns.map(col => (
             <button 
               key={col}
               onClick={() => setTargetColumn(col)}
               className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${targetColumn === col ? 'bg-indigo-600 text-white font-semibold shadow-md' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
             >
               {col}
             </button>
          ))}
        </div>
      </div>

      {/* Protected Attributes Selection */}
      <div className="glass p-6 rounded-2xl">
        <div className="flex items-center gap-2 mb-4">
          <div className="p-2 bg-rose-100 text-rose-600 rounded-lg">
            <Users className="w-5 h-5" />
          </div>
          <h3 className="text-lg font-bold">2. Protected Attributes</h3>
        </div>
        <p className="text-sm text-slate-500 mb-4">Select the demographic or sensitive columns to evaluate for bias (e.g., "sex", "race"). You can select multiple.</p>
        <div className="flex flex-wrap gap-2">
          {columns.map(col => {
             // Target can't be protected
             if (col === targetColumn) return null;
             const isSelected = protectedAttributes.includes(col);
             return (
               <button 
                 key={col}
                 onClick={() => toggleProtected(col)}
                 className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${isSelected ? 'bg-rose-500 text-white font-semibold shadow-md inline-flex items-center gap-1' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
               >
                 {col}
               </button>
             );
          })}
        </div>
      </div>
    </div>
  );
};
