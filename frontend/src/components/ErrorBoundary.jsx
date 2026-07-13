import React from "react";
import { AlertCircle } from 'lucide-react';

class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            hasError: false,
            error: null,
            errorInfo: null
        };
    }

    static getDerivedStateFromError(error) {
        return {
            hasError: true,
            error
        };
    }

    componentDidCatch(error, errorInfo) {
        console.error("ErrorBoundary caught:", error, errorInfo);
        this.setState({ errorInfo });
    }

    render() {
        if (this.state.hasError) {
            return (
                <div className="flex flex-col items-center justify-center min-h-screen bg-slate-50 p-6">
                    <div className="bg-white p-8 rounded-2xl shadow-sm border border-red-100 max-w-2xl w-full">
                        <div className="flex items-center gap-4 mb-6">
                            <div className="p-3 rounded-full bg-red-50 text-red-600">
                                <AlertCircle className="w-8 h-8" />
                            </div>
                            <div>
                                <h2 className="text-2xl font-bold text-slate-900">Something went wrong</h2>
                                <p className="text-slate-500 mt-1">An unexpected error occurred in the application.</p>
                            </div>
                        </div>
                        
                        <div className="bg-slate-900 rounded-xl p-4 overflow-auto max-h-96">
                            <pre className="text-red-400 font-mono text-sm whitespace-pre-wrap">
                                {this.state.error && this.state.error.toString()}
                                {'\n'}
                                {this.state.errorInfo && this.state.errorInfo.componentStack}
                            </pre>
                        </div>

                        <div className="mt-6 flex justify-end">
                            <button 
                                onClick={() => window.location.reload()}
                                className="px-6 py-2 bg-slate-900 text-white rounded-xl font-bold hover:bg-slate-800 transition-colors"
                            >
                                Reload Page
                            </button>
                        </div>
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;
