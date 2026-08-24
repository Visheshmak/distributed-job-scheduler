import React from 'react';
import {
  Layers,
  Activity,
  CheckCircle,
  AlertTriangle,
  Server,
  TrendingUp,
} from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
} from 'recharts';
import { OverviewMetrics, Queue, Job } from '../types';
import { MetricCard } from '../components/MetricCard';
import { StatusBadge } from '../components/StatusBadge';

interface HomeProps {
  metrics: OverviewMetrics | null;
  queues: Queue[];
  recentJobs: Job[];
  onSelectJob: (jobId: string) => void;
  onNavigateTab: (tab: string) => void;
}

export const Home: React.FC<HomeProps> = ({
  metrics,
  queues,
  recentJobs,
  onSelectJob,
  onNavigateTab,
}) => {
  if (!metrics) {
    return (
      <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
        Loading platform telemetry...
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* KPI Cards Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16 }}>
        <MetricCard
          title="Total Jobs Ingested"
          value={metrics.total_jobs.toLocaleString()}
          icon={<Layers size={20} />}
          subtitle={`${metrics.queued_jobs} currently in queue`}
          glowColor="rgba(99, 102, 241, 0.2)"
        />
        <MetricCard
          title="Running Executions"
          value={metrics.running_jobs}
          icon={<Activity size={20} />}
          subtitle="Distributed across worker slots"
          glowColor="rgba(6, 182, 212, 0.2)"
        />
        <MetricCard
          title="Completed Success"
          value={metrics.completed_jobs.toLocaleString()}
          icon={<CheckCircle size={20} />}
          subtitle="100% atomic execution"
          glowColor="rgba(16, 185, 129, 0.2)"
          trendPositive={true}
        />
        <MetricCard
          title="Dead Letter Queue"
          value={metrics.dlq_jobs}
          icon={<AlertTriangle size={20} />}
          subtitle="Exhausted retry limits"
          glowColor="rgba(239, 68, 68, 0.25)"
          trendPositive={false}
        />
        <MetricCard
          title="Active Workers"
          value={`${metrics.active_workers} / ${metrics.total_workers}`}
          icon={<Server size={20} />}
          subtitle={`Capacity Load: ${metrics.system_load_pct}%`}
          glowColor="rgba(168, 85, 247, 0.2)"
        />
      </div>

      {/* Real-time Charts Section */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 20 }}>
        {/* Throughput Area Chart */}
        <div className="glass-panel" style={{ padding: '20px 24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
            <div>
              <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#fff' }}>Execution Throughput</h3>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Completed vs Failed task attempts over time</p>
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--accent-secondary)', display: 'flex', alignItems: 'center', gap: 4 }}>
              <TrendingUp size={14} /> Live Telemetry
            </span>
          </div>

          <div style={{ height: 220, width: '100%' }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={metrics.throughput_history}>
                <defs>
                  <linearGradient id="compGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="failGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ef4444" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="timestamp" stroke="#4b5563" fontSize={11} tickLine={false} />
                <YAxis stroke="#4b5563" fontSize={11} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#111827',
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                />
                <Area type="monotone" dataKey="completed_count" stroke="#10b981" strokeWidth={2} fillOpacity={1} fill="url(#compGradient)" name="Completed" />
                <Area type="monotone" dataKey="failed_count" stroke="#ef4444" strokeWidth={2} fillOpacity={1} fill="url(#failGradient)" name="Failed / Retried" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Queue Depth Breakdown Bar Chart */}
        <div className="glass-panel" style={{ padding: '20px 24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
            <div>
              <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#fff' }}>Queue Depths</h3>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Queued vs Running per queue</p>
            </div>
            <button
              onClick={() => onNavigateTab('queues')}
              style={{ background: 'transparent', border: 'none', color: 'var(--accent-primary)', fontSize: '0.75rem', fontWeight: 600, cursor: 'pointer' }}
            >
              View All
            </button>
          </div>

          <div style={{ height: 220, width: '100%' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={metrics.queues}>
                <XAxis dataKey="queue_name" stroke="#4b5563" fontSize={10} tickLine={false} />
                <YAxis stroke="#4b5563" fontSize={11} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#111827',
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                />
                <Bar dataKey="queued_count" fill="#eab308" name="Queued" radius={[4, 4, 0, 0]} />
                <Bar dataKey="running_count" fill="#06b6d4" name="Running" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Active Work Queues & Recent Activity */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
        {/* Queues Status List */}
        <div className="glass-panel" style={{ padding: '20px 24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#fff' }}>Active Work Queues</h3>
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => onNavigateTab('queues')}
            >
              Manage
            </button>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {queues.map((q) => (
              <div
                key={q.id}
                style={{
                  padding: '12px 14px',
                  borderRadius: 8,
                  background: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid var(--border-subtle)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}
              >
                <div>
                  <div style={{ fontWeight: 600, fontSize: '0.875rem', color: '#fff' }}>{q.name}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    Priority: {q.priority} | Max Concurrency: {q.max_concurrency}
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                    <strong style={{ color: '#facc15' }}>{q.queued_count || 0}</strong> queued / <strong style={{ color: '#22d3ee' }}>{q.running_count || 0}</strong> running
                  </span>
                  <StatusBadge status={q.status} />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Jobs Feed */}
        <div className="glass-panel" style={{ padding: '20px 24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#fff' }}>Live Job Activity</h3>
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => onNavigateTab('jobs')}
            >
              Explorer
            </button>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {recentJobs.slice(0, 5).map((job) => (
              <div
                key={job.id}
                onClick={() => onSelectJob(job.id)}
                style={{
                  padding: '10px 14px',
                  borderRadius: 8,
                  background: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid var(--border-subtle)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  cursor: 'pointer',
                  transition: 'background 0.15s ease',
                }}
                onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255, 255, 255, 0.06)')}
                onMouseLeave={(e) => (e.currentTarget.style.background = 'rgba(255, 255, 255, 0.02)')}
              >
                <div>
                  <div style={{ fontWeight: 600, fontSize: '0.8125rem', color: '#fff' }}>{job.job_type}</div>
                  <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }} className="mono">
                    {job.id.substring(0, 8)}... | Priority: {job.priority}
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }}>
                    {new Date(job.created_at).toLocaleTimeString()}
                  </span>
                  <StatusBadge status={job.status} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
