"use client";
import React from "react";
import { Target, Users } from "lucide-react";

interface ColumnPickerProps {
  columns: string[];
  targetColumn: string;
  setTargetColumn: (col: string) => void;
  protectedAttributes: string[];
  setProtectedAttributes: (cols: string[]) => void;
}

export const ColumnPicker = ({
  columns,
  targetColumn,
  setTargetColumn,
  protectedAttributes,
  setProtectedAttributes,
}: ColumnPickerProps) => {
  const toggleProtected = (col: string) => {
    if (protectedAttributes.includes(col)) {
      setProtectedAttributes(protectedAttributes.filter((c) => c !== col));
    } else {
      setProtectedAttributes([...protectedAttributes, col]);
    }
  };

  return (
    <div className="mt-8 grid w-full gap-8 md:grid-cols-2 animate-slide-up">
      <div className="panel-soft p-6">
        <div className="mb-4 flex items-center gap-2">
          <div className="rounded-lg bg-cyan-400/10 p-2 text-cyan-300">
            <Target className="h-5 w-5" />
          </div>
          <h3 className="text-lg font-bold text-white">1. Target Variable</h3>
        </div>
        <p className="mb-4 text-sm text-cyan-50/55">
          Select the dependent variable your model is predicting.
        </p>
        <div className="flex flex-wrap gap-2">
          {columns.map((col) => (
            <button
              key={col}
              onClick={() => setTargetColumn(col)}
              className={`rounded-xl px-3 py-2 text-sm transition-colors ${
                targetColumn === col
                  ? "bg-cyan-300 font-semibold text-slate-950 shadow-md"
                  : "bg-cyan-400/8 text-cyan-50/72 hover:bg-cyan-400/12"
              }`}
            >
              {col}
            </button>
          ))}
        </div>
      </div>

      <div className="panel-soft p-6">
        <div className="mb-4 flex items-center gap-2">
          <div className="rounded-lg bg-fuchsia-500/10 p-2 text-fuchsia-300">
            <Users className="h-5 w-5" />
          </div>
          <h3 className="text-lg font-bold text-white">2. Protected Attributes</h3>
        </div>
        <p className="mb-4 text-sm text-cyan-50/55">
          Select the demographic or sensitive columns to evaluate for bias. You can select multiple.
        </p>
        <div className="flex flex-wrap gap-2">
          {columns.map((col) => {
            if (col === targetColumn) {
              return null;
            }
            const isSelected = protectedAttributes.includes(col);
            return (
              <button
                key={col}
                onClick={() => toggleProtected(col)}
                className={`rounded-xl px-3 py-2 text-sm transition-colors ${
                  isSelected
                    ? "inline-flex items-center gap-1 bg-fuchsia-500 font-semibold text-white shadow-md"
                    : "bg-cyan-400/8 text-cyan-50/72 hover:bg-cyan-400/12"
                }`}
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
