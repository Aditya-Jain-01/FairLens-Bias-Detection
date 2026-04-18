"use client";
import React, { useState, useRef } from 'react';
import { UploadCloud, CheckCircle } from 'lucide-react';

interface DropZoneProps {
  label: string;
  accept: string;
  onFileSelect: (file: File) => void;
  selectedFileName?: string;
  className?: string;
}

export const DropZone = ({ label, accept, onFileSelect, selectedFileName, className = "" }: DropZoneProps) => {
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
      className={`glass rounded-2xl p-8 border-2 border-dashed flex flex-col items-center justify-center cursor-pointer transition-colors ${isDragging ? 'border-indigo-500 bg-indigo-50' : 'border-slate-300 hover:border-indigo-400'} ${className}`}
    >
      <input 
        type="file" 
        accept={accept}
        className="hidden" 
        ref={fileInputRef} 
        onChange={handleChange} 
      />
      {selectedFileName ? (
        <div className="flex flex-col items-center text-emerald-600">
           <CheckCircle className="w-10 h-10 mb-4" />
           <p className="font-semibold text-center">{selectedFileName}</p>
        </div>
      ) : (
        <div className="flex flex-col items-center text-slate-500">
          <UploadCloud className="w-10 h-10 mb-4 text-indigo-400" />
          <p className="font-semibold">{label}</p>
          <p className="text-sm mt-2 opacity-80">Click or drag & drop</p>
        </div>
      )}
    </div>
  );
};
