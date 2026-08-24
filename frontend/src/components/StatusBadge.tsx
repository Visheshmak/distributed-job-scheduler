import React from 'react';
import { JobStatus, QueueStatus, WorkerStatus, DLQResolutionStatus } from '../types';

interface StatusBadgeProps {
  status: JobStatus | QueueStatus | WorkerStatus | DLQResolutionStatus | string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  const getStyle = () => {
    switch (status) {
      case 'QUEUED':
        return { bg: 'rgba(234, 179, 8, 0.15)', color: '#facc15', border: 'rgba(234, 179, 8, 0.3)' };
      case 'SCHEDULED':
        return { bg: 'rgba(59, 130, 246, 0.15)', color: '#60a5fa', border: 'rgba(59, 130, 246, 0.3)' };
      case 'CLAIMED':
        return { bg: 'rgba(139, 92, 246, 0.15)', color: '#a78bfa', border: 'rgba(139, 92, 246, 0.3)' };
      case 'RUNNING':
      case 'BUSY':
        return { bg: 'rgba(6, 182, 212, 0.15)', color: '#22d3ee', border: 'rgba(6, 182, 212, 0.3)', pulse: true };
      case 'COMPLETED':
      case 'ACTIVE':
      case 'IDLE':
      case 'REPLAYED':
        return { bg: 'rgba(16, 185, 129, 0.15)', color: '#34d399', border: 'rgba(16, 185, 129, 0.3)' };
      case 'FAILED':
      case 'UNHEALTHY':
      case 'DEAD_LETTER':
      case 'UNRESOLVED':
        return { bg: 'rgba(239, 68, 68, 0.15)', color: '#f87171', border: 'rgba(239, 68, 68, 0.3)' };
      case 'RETRY_PENDING':
        return { bg: 'rgba(249, 115, 22, 0.15)', color: '#fb923c', border: 'rgba(249, 115, 22, 0.3)' };
      case 'PAUSED':
      case 'STOPPED':
      case 'CANCELLED':
      case 'ARCHIVED':
      default:
        return { bg: 'rgba(156, 163, 175, 0.15)', color: '#9ca3af', border: 'rgba(156, 163, 175, 0.3)' };
    }
  };

  const style = getStyle();

  return (
    <span
      className="badge"
      style={{
        backgroundColor: style.bg,
        color: style.color,
        border: `1px solid ${style.border}`,
      }}
    >
      {style.pulse && (
        <span
          className="live-pulse"
          style={{ backgroundColor: style.color, marginRight: 2 }}
        />
      )}
      {status}
    </span>
  );
};
