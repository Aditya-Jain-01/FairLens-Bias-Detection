"use client";
import React, { useRef, useState } from "react";
import { CheckCircle, UploadCloud } from "lucide-react";

interface DropZoneProps {
  label: string;
  accept: string;
  onFileSelect: (file: File) => void;
  selectedFileName?: string;
  className?: string;
}

export const DropZone = ({
  label,
  accept,
  onFileSelect,
  selectedFileName,
  className = "",
}: DropZoneProps) => {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      onFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      onFileSelect(e.target.files[0]);
    }
  };

  return (
    <div
      onClick={() => fileInputRef.current?.click()}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={`panel-soft min-h-[240px] rounded-[28px] border-2 border-dashed p-8 transition-colors ${
        isDragging ? "border-cyan-300 bg-cyan-400/10" : "border-cyan-400/20 hover:border-cyan-300/40"
      } flex cursor-pointer flex-col items-center justify-center ${className}`}
    >
      <input
        type="file"
        accept={accept}
        className="hidden"
        ref={fileInputRef}
        onChange={handleChange}
      />
      {selectedFileName ? (
        <div className="flex flex-col items-center text-emerald-300">
          <CheckCircle className="mb-4 h-10 w-10" />
          <p className="text-center font-semibold text-white">{selectedFileName}</p>
          <p className="mt-2 text-sm text-cyan-50/55">File accepted and ready for processing</p>
        </div>
      ) : (
        <div className="flex flex-col items-center text-cyan-50/60">
          <UploadCloud className="mb-4 h-10 w-10 text-cyan-300" />
          <p className="font-semibold text-white">{label}</p>
          <p className="mt-2 text-sm opacity-80">Click or drag and drop</p>
        </div>
      )}
    </div>
  );
};
