import React, { useEffect, useState } from 'react';
import { X, RefreshCw, Slash, Clock, Terminal } from 'lucide-react';
import { JobDetail } from '../types';
import { api } from '../services/api';
import { StatusBadge } from './StatusBadge';

interface JobDetailsProps {
  jobId: string | null;
  onClose: () => void;
  onJobActionSuccess: () => void;
}

export const JobDetails: React.FC<JobDetailsProps> = ({
  jobId,
  onClose,
  onJobActionSuccess,
}) => {
  const [job, setJob] = useState<JobDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [selectedAttempt, setSelectedAttempt] = useState<number | null>(null);

  const fetchJob = async (id: string) => {
    setLoading(true);
    try {
      const data = await api.getJobDetail(id);
      setJob(data);
      if (data.executions && data.executions.length > 0) {
        setSelectedAttempt(data.executions[data.executions.length - 1].attempt_number);
      }
    } catch (err) {
      console.error('Failed to load job details', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (jobId) {
      fetchJob(jobId);
    } else {
      setJob(null);
    }
  }, [jobId]);

  if (!jobId) return null;

  const handleRetry = async () => {
    if (!job) return;
    setActionLoading(true);
    try {
      await api.retryJob(job.id);
      await fetchJob(job.id);
      onJobActionSuccess();
    } catch (err) {
      console.error('Retry failed', err);
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancel = async () => {
    if (!job) return;
    setActionLoading(true);
    try {
      await api.cancelJob(job.id);
      await fetchJob(job.id);
      onJobActionSuccess();
    } catch (err) {
      console.error('Cancel failed', err);
    } finally {
      setActionLoading(false);
    }
  };

  const currentExecution = job?.executions.find((e) => e.attempt_number === selectedAttempt);

  return (
    <div
      className="animate-fade-in"
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.65)',
        backdropFilter: 'blur(4px)',
        zIndex: 50,
        display: 'flex',
        justifyContent: 'flex-end',
      }}
      onClick={onClose}
    >
      <div
        className="glass-panel animate-slide-in"
        style={{
          width: '100%',
          maxWidth: '720px',
          height: '100vh',
          background: 'var(--bg-secondary)',
          borderLeft: '1px solid var(--border-subtle)',
          borderRadius: '0',
          boxShadow: '-10px 0 30px rgba(0,0,0,0.7)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#fff' }}>{job?.job_type || 'Job Details'}</h2>
              {job && <StatusBadge status={job.status} />}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }} className="mono">
              ID: {jobId}
            </div>
          </div>
          <button onClick={onClose} style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer' }}>
            <X size={22} />
          </button>
        </div>

        {loading || !job ? (
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
            <RefreshCw size={24} className="animate-spin" />
          </div>
        ) : (
          <div style={{ flex: 1, overflowY: 'auto', padding: '24px', display: 'flex', flexDirection: 'column', gap: 24 }}>
            {/* Quick Summary Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
              <div className="glass-panel" style={{ padding: '12px 16px' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Priority</div>
                <div style={{ fontSize: '1.125rem', fontWeight: 700 }}>{job.priority}</div>
              </div>
              <div className="glass-panel" style={{ padding: '12px 16px' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Attempts</div>
                <div style={{ fontSize: '1.125rem', fontWeight: 700 }}>
                  {job.attempt_count} / {job.max_retries}
                </div>
              </div>
              <div className="glass-panel" style={{ padding: '12px 16px' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Assigned Worker</div>
                <div style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--accent-secondary)' }} className="mono">
                  {job.claimed_by_worker_id || 'Unassigned'}
                </div>
              </div>
            </div>

            {/* Visual Chronological Execution Timeline */}
            <div>
              <h3 style={{ fontSize: '0.9375rem', fontWeight: 700, color: '#fff', marginBottom: 14, display: 'flex', alignItems: 'center', gap: 8 }}>
                <Clock size={16} color="var(--accent-primary)" />
                Audit & Execution Timeline
              </h3>
              <div style={{ position: 'relative', paddingLeft: 24, borderLeft: '2px solid var(--border-subtle)', marginLeft: 8, display: 'flex', flexDirection: 'column', gap: 18 }}>
                {job.timeline.map((item, idx) => (
                  <div key={idx} style={{ position: 'relative' }}>
                    {/* Timeline Node Dot */}
                    <div
                      style={{
                        position: 'absolute',
                        left: -31,
                        top: 2,
                        width: 12,
                        height: 12,
                        borderRadius: '50%',
                        backgroundColor:
                          item.status === 'COMPLETED'
                            ? '#10b981'
                            : item.status === 'FAILED' || item.status === 'DEAD_LETTER'
                            ? '#ef4444'
                            : item.status === 'RUNNING'
                            ? '#06b6d4'
                            : '#6366f1',
                        border: '2px solid var(--bg-secondary)',
                      }}
                    />
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span style={{ fontWeight: 600, fontSize: '0.875rem', color: '#fff' }}>{item.event}</span>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        {new Date(item.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                    {item.details && (
                      <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: 2 }}>
                        {item.details}
                      </p>
                    )}
                    {item.worker_id && (
                      <span style={{ fontSize: '0.6875rem', color: 'var(--accent-secondary)' }} className="mono">
                        by {item.worker_id}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Execution Attempt History & Streaming Logs */}
            {job.executions.length > 0 && (
              <div>
                <h3 style={{ fontSize: '0.9375rem', fontWeight: 700, color: '#fff', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Terminal size={16} color="var(--accent-secondary)" />
                  Execution Attempts & Captured Logs
                </h3>

                {/* Attempt Tabs */}
                <div style={{ display: 'flex', gap: 6, marginBottom: 12 }}>
                  {job.executions.map((exec) => (
                    <button
                      key={exec.attempt_number}
                      onClick={() => setSelectedAttempt(exec.attempt_number)}
                      className={`btn btn-sm ${selectedAttempt === exec.attempt_number ? 'btn-primary' : 'btn-secondary'}`}
                    >
                      Attempt #{exec.attempt_number} ({exec.status})
                    </button>
                  ))}
                </div>

                {currentExecution && (
                  <div
                    style={{
                      background: '#090d16',
                      borderRadius: 10,
                      padding: 14,
                      border: '1px solid var(--border-subtle)',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8, fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      <span>Worker: <strong style={{ color: '#fff' }}>{currentExecution.worker_id}</strong></span>
                      <span>Duration: <strong style={{ color: '#fff' }}>{currentExecution.duration_ms || 0}ms</strong></span>
                    </div>

                    {currentExecution.logs && currentExecution.logs.length > 0 ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 6, maxHeight: '200px', overflowY: 'auto' }} className="mono">
                        {currentExecution.logs.map((log) => (
                          <div key={log.id} style={{ fontSize: '0.75rem', display: 'flex', gap: 8 }}>
                            <span style={{ color: 'var(--text-muted)' }}>{new Date(log.timestamp).toLocaleTimeString()}</span>
                            <span style={{ color: log.log_level === 'ERROR' ? '#f87171' : log.log_level === 'WARN' ? '#fb923c' : '#34d399', fontWeight: 600 }}>
                              [{log.log_level}]
                            </span>
                            <span style={{ color: '#e5e7eb' }}>{log.message}</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>No logs captured for this execution attempt.</p>
                    )}

                    {currentExecution.stack_trace && (
                      <div style={{ marginTop: 10, paddingTop: 10, borderTop: '1px solid var(--border-subtle)' }}>
                        <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#f87171', marginBottom: 4 }}>Exception Stack Trace:</div>
                        <pre style={{ fontSize: '0.6875rem', color: '#fca5a5', overflowX: 'auto', background: 'rgba(0,0,0,0.5)', padding: 8, borderRadius: 6 }}>
                          {currentExecution.stack_trace}
                        </pre>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Payload Inspection */}
            <div>
              <h3 style={{ fontSize: '0.9375rem', fontWeight: 700, color: '#fff', marginBottom: 8 }}>Job Payload</h3>
              <pre className="mono" style={{ fontSize: '0.75rem', background: '#090d16', padding: 14, borderRadius: 8, border: '1px solid var(--border-subtle)', overflowX: 'auto' }}>
                {JSON.stringify(job.payload, null, 2)}
              </pre>
            </div>
          </div>
        )}

        {/* Footer Actions */}
        {job && (
          <div style={{ padding: '16px 24px', borderTop: '1px solid var(--border-subtle)', background: 'rgba(0,0,0,0.3)', display: 'flex', justifyContent: 'space-between' }}>
            <div>
              {['QUEUED', 'SCHEDULED'].includes(job.status) && (
                <button className="btn btn-danger btn-sm" onClick={handleCancel} disabled={actionLoading}>
                  <Slash size={14} /> Cancel Job
                </button>
              )}
            </div>
            <div style={{ display: 'flex', gap: 10 }}>
              {['FAILED', 'DEAD_LETTER', 'CANCELLED'].includes(job.status) && (
                <button className="btn btn-primary btn-sm" onClick={handleRetry} disabled={actionLoading}>
                  <RefreshCw size={14} /> Re-queue / Retry
                </button>
              )}
              <button className="btn btn-secondary btn-sm" onClick={onClose}>
                Close
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
