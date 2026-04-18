import Link from "next/link";
import { ArrowRight, ShieldCheck, Activity, FileText } from "lucide-react";

export default function Home() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[80vh] py-12 px-4 text-center animate-slide-up">
      <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-100 text-indigo-700 text-sm font-medium mb-8">
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-indigo-500"></span>
        </span>
        FairLens Engine 1.0 is Live
      </div>

      <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight text-slate-900 mb-6 max-w-4xl">
        Expose and Fix AI Bias <br />
        <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-500 to-purple-600">
          In Minutes.
        </span>
      </h1>

      <p className="text-xl text-slate-600 mb-10 max-w-2xl leading-relaxed">
        Enterprise-grade bias detection and remediation toolkit. Upload your predictions, identify protected attributes, and get actionable compliance reports.
      </p>

      <div className="flex flex-col sm:flex-row gap-4 mb-20 w-full sm:w-auto">
        <Link 
          href="/upload"
          className="inline-flex items-center justify-center px-8 py-4 text-lg font-semibold rounded-xl text-white bg-slate-900 hover:bg-slate-800 transition-all shadow-lg hover:shadow-xl hover:-translate-y-0.5 group"
        >
          Start new audit
          <ArrowRight className="ml-2 w-5 h-5 group-hover:translate-x-1 transition-transform" />
        </Link>
        <Link 
          href="/results/demo"
          className="inline-flex items-center justify-center px-8 py-4 text-lg font-semibold rounded-xl text-slate-700 bg-white border border-slate-200 hover:border-slate-300 hover:bg-slate-50 transition-all shadow-sm"
        >
          Explore interactive demo
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl w-full text-left">
        <div className="glass p-8 rounded-2xl card-hover">
          <div className="w-12 h-12 rounded-xl bg-indigo-100 text-indigo-600 flex items-center justify-center mb-6">
            <Activity className="w-6 h-6" />
          </div>
          <h3 className="text-xl font-bold mb-3 text-slate-900">Deep Analytics</h3>
          <p className="text-slate-600 leading-relaxed">
            Evaluate Disparate Impact, Equalized Odds, Demographic Parity, and Calibration across multiple demographic cuts.
          </p>
        </div>
        
        <div className="glass p-8 rounded-2xl card-hover">
          <div className="w-12 h-12 rounded-xl bg-purple-100 text-purple-600 flex items-center justify-center mb-6">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <h3 className="text-xl font-bold mb-3 text-slate-900">1-Click Remediation</h3>
          <p className="text-slate-600 leading-relaxed">
            Automatically mitigate discovered bias through reweighing and threshold calibration with quantified accuracy trade-offs.
          </p>
        </div>

        <div className="glass p-8 rounded-2xl card-hover">
          <div className="w-12 h-12 rounded-xl bg-emerald-100 text-emerald-600 flex items-center justify-center mb-6">
            <FileText className="w-6 h-6" />
          </div>
          <h3 className="text-xl font-bold mb-3 text-slate-900">Automated Reports</h3>
          <p className="text-slate-600 leading-relaxed">
            Generate compliant PDF reports powered by Gemini AI with simple plain-English explanations.
          </p>
        </div>
      </div>
    </div>
  );
}
