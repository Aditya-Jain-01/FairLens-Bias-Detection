"use client";
import React, { useState, useMemo } from "react";
import { Target, Users, HelpCircle, Sparkles } from "lucide-react";

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
  const [showGuide, setShowGuide] = useState(false);

  // ── Auto-suggest logic ──
  const suggestedColumns = useMemo(() => {
    const sensitiveKeywords = [
      "race", "sex", "gender", "age", "ethnic", "religion", 
      "marital", "disability", "national", "veteran", "orientation"
    ];
    return columns.filter(col => {
      const normalized = col.toLowerCase().replace(/[^a-z0-9]/g, "");
      return sensitiveKeywords.some(kw => normalized.includes(kw));
    });
  }, [columns]);

  const autoSelectSuggested = () => {
    // Only add suggested columns that are NOT the target column
    const toAdd = suggestedColumns.filter(c => c !== targetColumn && !protectedAttributes.includes(c));
    if (toAdd.length > 0) {
      setProtectedAttributes([...protectedAttributes, ...toAdd]);
    }
  };

  const toggleProtected = (col: string) => {
    if (protectedAttributes.includes(col)) {
      setProtectedAttributes(protectedAttributes.filter((c) => c !== col));
    } else {
      setProtectedAttributes([...protectedAttributes, col]);
    }
  };

  return (
    <div className="animate-slide-up w-full">
      {/* ── Guidance Banner ── */}
      <div className="mb-6 rounded-2xl border border-amber-600/20 bg-amber-500/5 p-5">
        <button 
          onClick={() => setShowGuide(!showGuide)}
          className="flex w-full items-center justify-between text-left font-semibold text-amber-950 dark:text-amber-100 transition-opacity hover:opacity-80"
        >
          <div className="flex items-center gap-2">
            <HelpCircle className="h-5 w-5 text-amber-600 dark:text-amber-400" />
            Guide: How to map your variables correctly
          </div>
          <span className="text-sm text-amber-700 dark:text-amber-400 font-medium">
            {showGuide ? "Hide Guide" : "Show Guide"}
          </span>
        </button>
        
        {showGuide && (
          <div className="mt-4 grid gap-6 md:grid-cols-2 text-sm text-amber-900/80 dark:text-amber-300/80 border-t border-amber-600/10 pt-5">
            <div>
              <h4 className="font-bold text-amber-950 dark:text-amber-100 flex items-center gap-1.5 mb-2">
                <Target className="h-4 w-4 text-amber-600 dark:text-amber-400" /> 
                1. Target Variable must be Binary
              </h4>
              <p>
                The target variable represents the outcome you are predicting. It <strong>must be a binary variable (0 or 1)</strong>, where 1 usually represents a positive outcome (e.g. Loan Approved).
              </p>
              <p className="mt-2 text-xs opacity-75">
                <strong>Why?</strong> Fairness metrics rely on calculating False Positive and True Positive rates. The engine cannot calculate this if you select a continuous number (like exact salary or house price).
              </p>
            </div>
            <div>
              <h4 className="font-bold text-amber-950 dark:text-amber-100 flex items-center gap-1.5 mb-2">
                <Users className="h-4 w-4 text-amber-600 dark:text-amber-400" /> 
                2. Protected Attributes must be Categorical
              </h4>
              <p>
                Protected attributes represent demographics. They <strong>must be categorical variables</strong> with a small number of distinct groups (e.g. Race, Sex, or Age brackets like "18-25").
              </p>
              <p className="mt-2 text-xs opacity-75">
                <strong>Why?</strong> Do not select continuous numbers (like exact age: 24) or unique identifiers (like customer_id). The system needs enough people in each bucket to calculate a statistically meaningful average.
              </p>
            </div>
          </div>
        )}
      </div>

      <div className="grid w-full gap-8 md:grid-cols-2">
        <div className="panel-soft p-6">
          <div className="mb-4 flex items-center gap-2">
            <div className="rounded-lg bg-amber-500/10 p-2 text-[#d97706] dark:text-amber-400">
              <Target className="h-5 w-5" />
            </div>
            <h3 className="text-lg font-bold text-amber-950 dark:text-amber-100">1. Target Variable</h3>
          </div>
          <p className="mb-4 text-sm text-amber-900/70 dark:text-amber-300/70">
            Select the dependent variable your model is predicting (must be 0/1).
          </p>
          <div className="flex flex-wrap gap-2">
            {columns.map((col) => (
              <button
                key={col}
                onClick={() => setTargetColumn(col)}
                className={`rounded-xl px-3 py-2 text-sm transition-all duration-200 ${
                  targetColumn === col
                    ? "bg-amber-500 font-semibold text-white shadow-md shadow-amber-500/20"
                    : "bg-amber-500/5 text-amber-900/70 dark:bg-amber-400/5 dark:text-amber-300/70 hover:bg-amber-500/15 dark:hover:bg-amber-400/15"
                }`}
              >
                {col}
              </button>
            ))}
          </div>
        </div>

        <div className="panel-soft p-6">
          <div className="mb-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="rounded-lg bg-amber-500/10 p-2 text-[#d97706] dark:text-amber-400">
                <Users className="h-5 w-5" />
              </div>
              <h3 className="text-lg font-bold text-amber-950 dark:text-amber-100">2. Protected Attributes</h3>
            </div>
            
            {suggestedColumns.length > 0 && (
              <button
                onClick={autoSelectSuggested}
                className="text-xs font-semibold flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-amber-500/15 text-amber-700 dark:text-amber-400 hover:bg-amber-500/25 transition-colors border border-amber-500/20"
              >
                <Sparkles className="h-3 w-3" />
                Auto-Select Suggested
              </button>
            )}
          </div>
          <p className="mb-4 text-sm text-amber-900/70 dark:text-amber-300/70">
            Select the demographic columns to evaluate for bias (categorical only).
          </p>
          <div className="flex flex-wrap gap-2">
            {columns.map((col) => {
              if (col === targetColumn) {
                return null;
              }
              const isSelected = protectedAttributes.includes(col);
              const isSuggested = suggestedColumns.includes(col);
              return (
                <button
                  key={col}
                  onClick={() => toggleProtected(col)}
                  className={`rounded-xl px-3 py-2 text-sm transition-all duration-200 flex items-center gap-1.5 ${
                    isSelected
                      ? "bg-amber-600 font-semibold text-white shadow-md shadow-amber-600/20"
                      : isSuggested
                      ? "bg-amber-500/10 text-amber-900 dark:text-amber-200 border border-amber-500/40 hover:bg-amber-500/20 shadow-[0_0_10px_rgba(245,158,11,0.15)] font-medium"
                      : "bg-amber-500/5 text-amber-900/70 dark:bg-amber-400/5 dark:text-amber-300/70 hover:bg-amber-500/15 dark:hover:bg-amber-400/15"
                  }`}
                >
                  {isSuggested && !isSelected && <Sparkles className="h-3 w-3 text-amber-500" />}
                  {col}
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};
