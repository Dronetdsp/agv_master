/**
 * Progress bar component with status indicator
 */
import React from 'react';
import { Loader2, CheckCircle, XCircle } from 'lucide-react';

interface ProgressBarProps {
  progress: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  message?: string;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
  progress,
  status,
  message,
}) => {
  const getStatusIcon = () => {
    switch (status) {
      case 'pending':
      case 'processing':
        return <Loader2 className="w-5 h-5 animate-spin text-blue-500" />;
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-500" />;
    }
  };

  const getStatusColor = () => {
    switch (status) {
      case 'pending':
        return 'bg-gray-400';
      case 'processing':
        return 'bg-blue-500';
      case 'completed':
        return 'bg-green-500';
      case 'failed':
        return 'bg-red-500';
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        {getStatusIcon()}
        <div className="flex-1">
          <div className="flex justify-between items-center mb-1">
            <span className="text-sm font-medium capitalize">{status}</span>
            <span className="text-sm text-gray-600">{Math.round(progress)}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2.5">
            <div
              className={`h-2.5 rounded-full transition-all duration-300 ${getStatusColor()}`}
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      </div>
      {message && (
        <p className="text-sm text-gray-600 ml-8">{message}</p>
      )}
    </div>
  );
};
