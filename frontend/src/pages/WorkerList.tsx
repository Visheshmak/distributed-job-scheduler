import React, { useState } from 'react';
import { Server, Clock, Plus, Loader2 } from 'lucide-react';
import { Worker } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { api } from '../services/api';

interface WorkerListProps {
  workers: Worker[];
}

export const WorkerList: React.FC<WorkerListProps> = ({ workers }) => {
  const [isSpawning, setIsSpawning] = useState(false);

  const handleSpawnWorker = async () => {
    try {
      setIsSpawning(true);
      await api.spawnWorker();
      // Wait for UI polling to pick up the new worker
      setTimeout(() => {
        setIsSpawning(false);
      }, 2000);
    } catch (err) {
      console.error('Failed to spawn worker:', err);
      setIsSpawning(false);
    }
  };

  const formatUptime = (seconds?: number) => {
    if (!seconds) return '0s';
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    if (hrs > 0) return `${hrs}h ${mins}m`;
    if (mins > 0) return `${mins}m ${secs}s`;
    return `${secs}s`;
  };

  const getHeartbeatAgeSeconds = (timestamp: string) => {
    const diff = Math.floor((Date.now() - new Date(timestamp).getTime()) / 1000);
    return Math.max(0, diff);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Worker Fleet</h1>
          <p className="text-sm text-text-muted">
            Real-time status of all distributed processing nodes. 
          </p>
        </div>
        <button 
          onClick={handleSpawnWorker} 
          disabled={isSpawning}
          className="btn btn-primary"
          style={{ display: 'flex', alignItems: 'center', gap: 6 }}
        >
          {isSpawning ? <Loader2 size={16} className="animate-spin" /> : <Plus size={16} />}
          {isSpawning ? 'Spawning...' : 'Spawn Worker Node'}
        </button>
      </div>

      {/* Worker Cards Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 16 }}>
        {workers.map((w) => {
          const heartbeatAge = getHeartbeatAgeSeconds(w.last_heartbeat_at);
          const loadPct = Math.round((w.current_running_jobs / w.concurrency) * 100);

          return (
            <div key={w.worker_id} className="glass-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: 14 }}>
              {/* Card Header */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <div
                    style={{
                      padding: 8,
                      borderRadius: 8,
                      background: w.is_healthy ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                      color: w.is_healthy ? '#34d399' : '#f87171',
                    }}
                  >
                    <Server size={20} />
                  </div>
                  <div>
                    <h3 style={{ fontSize: '0.9375rem', fontWeight: 700, color: '#fff' }} className="mono">
                      {w.worker_id}
                    </h3>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      Host: {w.hostname}
                    </span>
                  </div>
                </div>
                <StatusBadge status={w.status} />
              </div>

              {/* Concurrency Slot Capacity Progress Bar */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: 6 }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Capacity Utilization</span>
                  <span style={{ fontWeight: 600, color: loadPct > 80 ? '#fb923c' : 'var(--accent-secondary)' }}>
                    {w.current_running_jobs} / {w.concurrency} slots ({loadPct}%)
                  </span>
                </div>
                <div style={{ width: '100%', height: 6, background: 'rgba(255, 255, 255, 0.08)', borderRadius: 4, overflow: 'hidden' }}>
                  <div
                    style={{
                      width: `${Math.min(100, loadPct)}%`,
                      height: '100%',
                      background: loadPct > 80 ? 'linear-gradient(90deg, #f59e0b, #ef4444)' : 'linear-gradient(90deg, var(--accent-primary), var(--accent-secondary))',
                      borderRadius: 4,
                      transition: 'width 0.3s ease',
                    }}
                  />
                </div>
              </div>

              {/* Heartbeat & Uptime Telemetry */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, paddingTop: 10, borderTop: '1px solid var(--border-subtle)', fontSize: '0.75rem' }}>
                <div>
                  <div style={{ color: 'var(--text-muted)', marginBottom: 2 }}>Last Heartbeat</div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontWeight: 600, color: heartbeatAge > 15 ? '#f87171' : '#34d399' }}>
                    <Clock size={12} />
                    {heartbeatAge}s ago
                  </div>
                </div>
                <div>
                  <div style={{ color: 'var(--text-muted)', marginBottom: 2 }}>Uptime</div>
                  <div style={{ fontWeight: 600, color: '#fff' }}>
                    {formatUptime(w.uptime_seconds)}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
