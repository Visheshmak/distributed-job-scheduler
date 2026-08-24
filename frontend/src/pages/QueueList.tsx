import React, { useState } from 'react';
import { Plus, Pause, Play } from 'lucide-react';
import { Queue, Project, RetryPolicy } from '../types';
import { api } from '../services/api';
import { StatusBadge } from '../components/StatusBadge';

interface QueueListProps {
  queues: Queue[];
  projects: Project[];
  retryPolicies: RetryPolicy[];
  onRefresh: () => void;
}

export const QueueList: React.FC<QueueListProps> = ({
  queues,
  projects,
  retryPolicies,
  onRefresh,
}) => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [name, setName] = useState('');
  const [priority, setPriority] = useState(5);
  const [maxConcurrency, setMaxConcurrency] = useState(10);
  const [selectedPolicyId, setSelectedPolicyId] = useState('');
  const [loading, setLoading] = useState(false);

  const defaultProjectId = projects[0]?.id || '';

  const handleToggleStatus = async (queue: Queue) => {
    try {
      if (queue.status === 'ACTIVE') {
        await api.pauseQueue(queue.id);
      } else {
        await api.resumeQueue(queue.id);
      }
      onRefresh();
    } catch (err) {
      console.error('Failed to toggle queue status', err);
    }
  };

  const handleCreateQueue = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await api.createQueue({
        project_id: defaultProjectId,
        name: name.trim(),
        priority: Number(priority),
        max_concurrency: Number(maxConcurrency),
        retry_policy_id: selectedPolicyId || undefined,
      });
      setIsModalOpen(false);
      setName('');
      onRefresh();
    } catch (err: any) {
      alert(err.message || 'Failed to create queue');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#fff' }}>Queue Configurations</h2>
          <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
            Manage worker concurrency limits, priorities, and retry policies per queue
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => setIsModalOpen(true)}>
          <Plus size={16} /> Create Queue
        </button>
      </div>

      {/* Queues Table */}
      <div className="glass-panel" style={{ overflow: 'hidden' }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>Queue Name</th>
              <th>Status</th>
              <th>Priority</th>
              <th>Concurrency Limit</th>
              <th>Retry Policy</th>
              <th>Queued / Running</th>
              <th>Completed / Failed</th>
              <th style={{ textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {queues.map((q) => (
              <tr key={q.id}>
                <td>
                  <div style={{ fontWeight: 600, color: '#fff' }}>{q.name}</div>
                  <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }} className="mono">
                    {q.id.substring(0, 8)}...
                  </div>
                </td>
                <td>
                  <StatusBadge status={q.status} />
                </td>
                <td>
                  <span className="badge" style={{ background: 'rgba(255,255,255,0.06)', color: '#fff' }}>
                    {q.priority}
                  </span>
                </td>
                <td>
                  <span style={{ fontWeight: 600, color: 'var(--accent-secondary)' }}>
                    {q.max_concurrency} slots
                  </span>
                </td>
                <td>
                  <span style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
                    {q.retry_policy?.name || 'Default Exponential'}
                  </span>
                </td>
                <td>
                  <span style={{ color: '#facc15', fontWeight: 600 }}>{q.queued_count || 0}</span>
                  <span style={{ color: 'var(--text-muted)' }}> / </span>
                  <span style={{ color: '#22d3ee', fontWeight: 600 }}>{q.running_count || 0}</span>
                </td>
                <td>
                  <span style={{ color: '#34d399', fontWeight: 600 }}>{q.completed_count || 0}</span>
                  <span style={{ color: 'var(--text-muted)' }}> / </span>
                  <span style={{ color: '#f87171', fontWeight: 600 }}>{q.failed_count || 0}</span>
                </td>
                <td style={{ textAlign: 'right' }}>
                  <button
                    className={`btn btn-sm ${q.status === 'ACTIVE' ? 'btn-danger' : 'btn-success'}`}
                    onClick={() => handleToggleStatus(q)}
                  >
                    {q.status === 'ACTIVE' ? (
                      <>
                        <Pause size={13} /> Pause
                      </>
                    ) : (
                      <>
                        <Play size={13} /> Resume
                      </>
                    )}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Create Queue Modal */}
      {isModalOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.7)',
            backdropFilter: 'blur(4px)',
            zIndex: 50,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 16,
          }}
          onClick={() => setIsModalOpen(false)}
        >
          <div
            className="glass-panel"
            style={{ width: '100%', maxWidth: '480px', background: 'var(--bg-modal)', padding: 24, borderRadius: 16 }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ fontSize: '1.125rem', fontWeight: 700, color: '#fff', marginBottom: 16 }}>Create Work Queue</h3>
            <form onSubmit={handleCreateQueue} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div>
                <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4, display: 'block' }}>Queue Name</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. high-priority-sync"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div>
                  <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4, display: 'block' }}>Priority</label>
                  <input
                    type="number"
                    className="form-input"
                    value={priority}
                    onChange={(e) => setPriority(Number(e.target.value))}
                  />
                </div>
                <div>
                  <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4, display: 'block' }}>Max Concurrency</label>
                  <input
                    type="number"
                    className="form-input"
                    value={maxConcurrency}
                    onChange={(e) => setMaxConcurrency(Number(e.target.value))}
                    min={1}
                    max={100}
                  />
                </div>
              </div>

              <div>
                <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4, display: 'block' }}>Retry Policy</label>
                <select
                  className="form-input"
                  value={selectedPolicyId}
                  onChange={(e) => setSelectedPolicyId(e.target.value)}
                >
                  <option value="">Default Exponential Backoff (4 attempts)</option>
                  {retryPolicies.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.strategy} - {p.max_attempts} max attempts)
                    </option>
                  ))}
                </select>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 8 }}>
                <button type="button" className="btn btn-secondary" onClick={() => setIsModalOpen(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={loading}>
                  {loading ? 'Creating...' : 'Create Queue'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
