import React from 'react';
import { Layers, Activity, ListOrdered, Server, AlertTriangle, PlusCircle, Play, RefreshCw, Zap } from 'lucide-react';

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  dlqCount: number;
  activeWorkers: number;
  onOpenSubmitModal: () => void;
  onTriggerDemo: () => void;
  onRefresh: () => void;
  isRefreshing: boolean;
  refreshInterval: number;
  setRefreshInterval: (interval: number) => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  dlqCount,
  activeWorkers,
  onOpenSubmitModal,
  onTriggerDemo,
  onRefresh,
  isRefreshing,
  refreshInterval,
  setRefreshInterval,
}) => {
  const tabs = [
    { id: 'overview', label: 'Overview', icon: <Activity size={18} /> },
    { id: 'queues', label: 'Queues', icon: <Layers size={18} /> },
    { id: 'jobs', label: 'Job Explorer', icon: <ListOrdered size={18} /> },
    { id: 'workers', label: 'Workers', icon: <Server size={18} />, badge: activeWorkers },
    { id: 'dlq', label: 'DLQ', icon: <AlertTriangle size={18} />, badge: dlqCount, badgeColor: '#ef4444' },
  ];

  return (
    <header
      style={{
        borderBottom: '1px solid var(--border-subtle)',
        background: 'rgba(10, 14, 23, 0.85)',
        backdropFilter: 'blur(16px)',
        position: 'sticky',
        top: 0,
        zIndex: 40,
        padding: '0 24px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: '64px' }}>
        {/* Brand */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div
            style={{
              width: 38,
              height: 38,
              borderRadius: 10,
              background: 'linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 15px rgba(99, 102, 241, 0.5)',
            }}
          >
            <Zap size={22} color="#fff" />
          </div>
          <div>
            <div style={{ fontSize: '1rem', fontWeight: 800, letterSpacing: '-0.02em', color: '#fff' }}>
              DISTRIBUTED JOB <span style={{ color: 'var(--accent-secondary)' }}>SCHEDULER</span>
            </div>
            <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)', fontWeight: 500 }}>
              Distributed Job Coordination Platform
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav style={{ display: 'flex', gap: 6 }}>
          {tabs.map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '8px 16px',
                  borderRadius: 8,
                  fontSize: '0.875rem',
                  fontWeight: isActive ? 600 : 500,
                  color: isActive ? '#fff' : 'var(--text-secondary)',
                  background: isActive ? 'rgba(99, 102, 241, 0.15)' : 'transparent',
                  border: isActive ? '1px solid rgba(99, 102, 241, 0.4)' : '1px solid transparent',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
              >
                {tab.icon}
                {tab.label}
                {tab.badge !== undefined && tab.badge > 0 && (
                  <span
                    style={{
                      fontSize: '0.7rem',
                      padding: '1px 6px',
                      borderRadius: 9999,
                      background: tab.badgeColor ? 'rgba(239, 68, 68, 0.25)' : 'rgba(99, 102, 241, 0.3)',
                      color: tab.badgeColor || '#a5b4fc',
                      fontWeight: 700,
                    }}
                  >
                    {tab.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {/* Polling interval selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 4, background: 'rgba(255, 255, 255, 0.04)', padding: '4px 8px', borderRadius: 8, border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Auto:</span>
            <select
              value={refreshInterval}
              onChange={(e) => setRefreshInterval(Number(e.target.value))}
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--text-secondary)',
                fontSize: '0.75rem',
                outline: 'none',
                cursor: 'pointer',
              }}
            >
              <option value={2000} style={{ background: '#111827' }}>2s</option>
              <option value={5000} style={{ background: '#111827' }}>5s</option>
              <option value={10000} style={{ background: '#111827' }}>10s</option>
              <option value={0} style={{ background: '#111827' }}>Paused</option>
            </select>
          </div>

          <button
            className="btn btn-secondary btn-sm"
            onClick={onRefresh}
            title="Refresh current data"
            disabled={isRefreshing}
          >
            <RefreshCw size={14} className={isRefreshing ? 'animate-spin' : ''} />
          </button>

          <button
            className="btn btn-secondary btn-sm"
            onClick={onTriggerDemo}
            title="Inject simulated concurrent demo workloads"
            style={{ color: 'var(--accent-secondary)', borderColor: 'rgba(6, 182, 212, 0.3)' }}
          >
            <Play size={14} />
            Demo Batch
          </button>

          <button className="btn btn-primary btn-sm" onClick={onOpenSubmitModal}>
            <PlusCircle size={15} />
            Submit Job
          </button>
        </div>
      </div>
    </header>
  );
};
