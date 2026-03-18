'use client';

import { useState, FormEvent } from 'react';
import { Stethoscope, Lock, User, ArrowRight, AlertCircle } from 'lucide-react';

export default function LoginPage() {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    // Since we are proxying to Flask, we can just use a standard form submission
    // or handle it via fetch if we want more control. For simplicity and to match
    // Flask-Login's expectation of form data, we'll use a form action but 
    // we might need to handle the redirect manually if we want a SPA feel.
    // However, since Flask-Login sets a cookie, a standard form post to /login 
    // (which is proxied) is the most robust way to start.

    return (
        <main className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
            <div className="max-w-md w-full bg-white rounded-2xl shadow-xl overflow-hidden border border-slate-100">
                {/* Header */}
                <div className="bg-blue-600 p-8 text-center">
                    <div className="mx-auto bg-white/20 w-16 h-16 rounded-full flex items-center justify-center mb-4 backdrop-blur-sm">
                        <Stethoscope className="h-8 w-8 text-white" />
                    </div>
                    <h1 className="text-2xl font-bold text-white mb-2">Medical RAG Neo</h1>
                    <p className="text-blue-100 text-sm">Secure Clinical Intelligence Platform</p>
                </div>

                {/* Form */}
                <div className="p-8">
                    <form action="/login" method="POST" className="space-y-6">
                        <div>
                            <label className="block text-sm font-medium text-slate-700 mb-2">Username</label>
                            <div className="relative">
                                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                    <User className="h-5 w-5 text-slate-400" />
                                </div>
                                <input
                                    type="text"
                                    name="username"
                                    required
                                    className="block w-full pl-10 pr-3 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
                                    placeholder="Enter your username"
                                />
                            </div>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-slate-700 mb-2">Password</label>
                            <div className="relative">
                                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                    <Lock className="h-5 w-5 text-slate-400" />
                                </div>
                                <input
                                    type="password"
                                    name="password"
                                    required
                                    className="block w-full pl-10 pr-3 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
                                    placeholder="••••••••"
                                />
                            </div>
                        </div>

                        <button
                            type="submit"
                            className="w-full bg-slate-900 text-white py-3 rounded-xl font-semibold hover:bg-slate-800 transition-colors flex items-center justify-center gap-2 group"
                        >
                            Sign In
                            <ArrowRight className="h-4 w-4 group-hover:translate-x-0.5 transition-transform" />
                        </button>
                    </form>

                    <div className="mt-8 text-center">
                        <p className="text-xs text-slate-400">
                            Authorized personnel only. All access is logged.
                        </p>
                    </div>
                </div>
            </div>
        </main>
    );
}
