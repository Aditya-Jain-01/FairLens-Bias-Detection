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
          <div className="rounded-lg bg-amber-500/10 p-2 text-[#d97706]">
            <Target className="h-5 w-5" />
          </div>
          <h3 className="text-lg font-bold text-amber-950">1. Target Variable</h3>
        </div>
        <p className="mb-4 text-sm text-amber-900/70">
          Select the dependent variable your model is predicting.
        </p>
        <div className="flex flex-wrap gap-2">
          {columns.map((col) => (
            <button
              key={col}
              onClick={() => setTargetColumn(col)}
              className={`rounded-xl px-3 py-2 text-sm transition-colors ${
                targetColumn === col
                  ? "bg-amber-400 font-semibold text-amber-950 shadow-md"
                  : "bg-amber-500/5 text-amber-900/70 hover:bg-amber-500/15"
              }`}
            >
              {col}
            </button>
          ))}
        </div>
      </div>

      <div className="panel-soft p-6">
        <div className="mb-4 flex items-center gap-2">
          <div className="rounded-lg bg-amber-500/10 p-2 text-[#d97706]">
            <Users className="h-5 w-5" />
          </div>
          <h3 className="text-lg font-bold text-amber-950">2. Protected Attributes</h3>
        </div>
        <p className="mb-4 text-sm text-amber-900/70">
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
                    ? "inline-flex items-center gap-1 bg-[#d97706] font-semibold text-white shadow-md"
                    : "bg-amber-500/5 text-amber-900/70 hover:bg-amber-500/15"
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
