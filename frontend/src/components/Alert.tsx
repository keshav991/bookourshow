import React from 'react';
import { AlertCircle, CheckCircle, Info, X } from 'lucide-react';

interface AlertProps {
  type?: 'error' | 'success' | 'info';
  message: string;
  onClose?: () => void;
  className?: string;
}

export const Alert: React.FC<AlertProps> = ({ type = 'error', message, onClose, className = '' }) => {
  const configs = {
    error: {
      bg: 'bg-red-950/70 border-red-800/80 text-red-200',
      icon: <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />,
    },
    success: {
      bg: 'bg-emerald-950/70 border-emerald-800/80 text-emerald-200',
      icon: <CheckCircle className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />,
    },
    info: {
      bg: 'bg-sky-950/70 border-sky-800/80 text-sky-200',
      icon: <Info className="w-5 h-5 text-sky-400 shrink-0 mt-0.5" />,
    },
  };

  const current = configs[type];

  return (
    <div className={`flex items-start gap-3 p-4 rounded-xl border text-sm backdrop-blur-md ${current.bg} ${className}`}>
      {current.icon}
      <div className="flex-1 font-medium leading-relaxed">{message}</div>
      {onClose && (
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-white transition-colors p-1 -mr-1"
          aria-label="Dismiss alert"
        >
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  );
};
