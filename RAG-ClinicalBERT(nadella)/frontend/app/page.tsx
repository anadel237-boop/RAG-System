'use client';

import { useState, FormEvent } from 'react';
import { Search, Activity, FileText, Clock, AlertCircle, ChevronRight, Stethoscope } from 'lucide-react';

interface SearchResult {
  answer: string;
  confidence: number;
  processing_time: number;
  sources: string[];
  relevant_cases: number;
}

export default function Home() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SearchResult | null>(null);
  const [error, setError] = useState('');

  const handleSearch = async (e: FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError('');
    setResult(null);

    try {
      const response = await fetch('/api/medical_query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      });

      if (!response.ok) {
        if (response.status === 401 || response.status === 403) {
          // Redirect to login if unauthorized
          window.location.href = '/login';
          return;
        }
        throw new Error('Failed to fetch results');
      }

      const data = await response.json();
      if (data.success) {
        setResult(data);
      } else {
        setError(data.error || 'An unknown error occurred');
      }
    } catch (err) {
      setError('System error. Please try again later.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2 text-blue-600">
            <Stethoscope className="h-8 w-8" />
            <span className="font-bold text-xl tracking-tight">Medical RAG Neo</span>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-sm text-slate-500 hidden sm:block">Dr. Admin</div>
            <a href="/logout" className="text-sm font-medium text-slate-600 hover:text-blue-600 transition-colors">
              Logout
            </a>
          </div>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-4 py-12">
        {/* Hero / Search Section */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-extrabold text-slate-900 mb-4 tracking-tight">
            Clinical Intelligence Assistant
          </h1>
          <p className="text-lg text-slate-600 mb-8 max-w-2xl mx-auto">
            Search across thousands of medical cases using advanced semantic retrieval.
          </p>

          <form onSubmit={handleSearch} className="max-w-2xl mx-auto relative">
            <div className="relative group">
              <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                <Search className={`h-6 w-6 ${loading ? 'text-blue-500 animate-pulse' : 'text-slate-400'}`} />
              </div>
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="block w-full pl-12 pr-4 py-4 bg-white border border-slate-200 rounded-2xl text-lg shadow-sm placeholder:text-slate-400 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none"
                placeholder="Describe symptoms, diagnosis, or treatment..."
                disabled={loading}
              />
              <button
                type="submit"
                disabled={loading || !query.trim()}
                className="absolute right-2 top-2 bottom-2 bg-blue-600 text-white px-6 rounded-xl font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {loading ? 'Analyzing...' : 'Search'}
              </button>
            </div>
          </form>
        </div>

        {/* Error State */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-8 flex items-start gap-3 text-red-700">
            <AlertCircle className="h-5 w-5 mt-0.5 flex-shrink-0" />
            <p>{error}</p>
          </div>
        )}

        {/* Results Section */}
        {result && (
          <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center gap-3">
                <div className="p-2 bg-green-100 rounded-lg text-green-600">
                  <Activity className="h-5 w-5" />
                </div>
                <div>
                  <div className="text-sm text-slate-500">Confidence</div>
                  <div className="font-bold text-slate-900">{(result.confidence * 100).toFixed(1)}%</div>
                </div>
              </div>
              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center gap-3">
                <div className="p-2 bg-blue-100 rounded-lg text-blue-600">
                  <FileText className="h-5 w-5" />
                </div>
                <div>
                  <div className="text-sm text-slate-500">Cases Analyzed</div>
                  <div className="font-bold text-slate-900">{result.relevant_cases}</div>
                </div>
              </div>
              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center gap-3">
                <div className="p-2 bg-purple-100 rounded-lg text-purple-600">
                  <Clock className="h-5 w-5" />
                </div>
                <div>
                  <div className="text-sm text-slate-500">Processing Time</div>
                  <div className="font-bold text-slate-900">{result.processing_time.toFixed(2)}s</div>
                </div>
              </div>
            </div>

            {/* Main Answer Card */}
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
              <div className="border-b border-slate-100 bg-slate-50/50 px-6 py-4">
                <h2 className="font-semibold text-slate-900 flex items-center gap-2">
                  <Activity className="h-5 w-5 text-blue-600" />
                  Clinical Analysis
                </h2>
              </div>
              <div className="p-6 prose prose-slate max-w-none">
                <div className="whitespace-pre-wrap text-slate-700 leading-relaxed">
                  {result.answer}
                </div>
              </div>
            </div>

            {/* Sources */}
            {result.sources && result.sources.length > 0 && (
              <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
                <h3 className="text-sm font-semibold text-slate-900 uppercase tracking-wider mb-4">
                  Referenced Sources
                </h3>
                <div className="flex flex-wrap gap-2">
                  {result.sources.map((source, idx) => (
                    <span
                      key={idx}
                      className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-600 border border-slate-200"
                    >
                      <FileText className="h-3 w-3 mr-1.5" />
                      {source}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </main>
  );
}
