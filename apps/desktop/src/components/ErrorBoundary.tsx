import React, { Component, type ErrorInfo, type ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { LoggingService } from '../services';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  errorMessage?: string;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, errorMessage: error.message };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    LoggingService.error('Renderer', `React Error Boundary caught exception: ${error.message}`, {
      stack: error.stack,
      componentStack: errorInfo.componentStack,
    });

    try {
      if (typeof window !== 'undefined' && window.system?.reportCrash) {
        void window.system.reportCrash({
          message: error.message,
          stack: error.stack,
          componentStack: errorInfo.componentStack,
        });
      }
    } catch {
      // Ignore IPC error reporting failures
    }
  }

  private handleReload = (): void => {
    window.location.reload();
  };

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-slate-950 text-slate-50 p-6 font-sans">
          <div className="max-w-md w-full bg-slate-900 border border-slate-800 rounded-xl p-8 text-center space-y-6 shadow-2xl">
            <div className="w-16 h-16 bg-danger/10 rounded-2xl flex items-center justify-center mx-auto text-danger">
              <AlertTriangle className="w-8 h-8" />
            </div>

            <div className="space-y-2">
              <h1 className="text-xl font-bold tracking-tight text-slate-100">Application Encountered an Error</h1>
              <p className="text-xs text-slate-400 leading-relaxed">
                An unexpected runtime error occurred. Diagnostic information has been captured by the structured logging system.
              </p>
            </div>

            {this.state.errorMessage && (
              <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 text-left font-mono text-xs text-danger overflow-x-auto">
                {this.state.errorMessage}
              </div>
            )}

            <button
              onClick={this.handleReload}
              className="w-full py-2.5 px-4 rounded-lg bg-primary-600 hover:bg-primary-500 text-white font-medium text-sm transition-colors flex items-center justify-center gap-2 cursor-pointer shadow-lg shadow-primary-500/20"
            >
              <RefreshCw className="w-4 h-4" /> Reload Application
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
