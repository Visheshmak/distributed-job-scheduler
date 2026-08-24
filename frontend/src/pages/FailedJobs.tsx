import React, { useState, useEffect } from 'react';
import { RotateCcw, Archive, RefreshCw, ChevronLeft, ChevronRight, FileText, Sparkles } from 'lucide-react';
import { DLQEntry, PagedResponse } from '../types';
import { api } from '../services/api';
import { StatusBadge } from '../components/StatusBadge';

interface FailedJobsProps {
  onSelectJob: (jobId: string) => void;
  onRefreshDLQ: () => void;
  refreshTrigger: number;
}

export const FailedJobs: React.FC<FailedJobsProps> = ({
  onSelectJob,
  onRefreshDLQ,
  refreshTrigger,
}) => {
  const [pagedDLQ, setPagedDLQ] = useState<PagedResponse<DLQEntry> | null>(null);
  const [page, setPage] = useState(0);
  const [size] = useState(15);
  const [loading, setLoading] = useState(false);
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);

  const fetchDLQ = async () => {
    setLoading(true);
    try {
      const data = await api.getDLQ({ page, size });
      setPagedDLQ(data);
    } catch (err) {
      console.error('Failed to load DLQ entries', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDLQ();
  }, [page, refreshTrigger]);

  const handleReplay = async (dlqId: string) => {
    setActionLoadingId(dlqId);
    try {
      await api.replayDLQ(dlqId);
      await fetchDLQ();
      onRefreshDLQ();
    } catch (err: any) {
      alert(err.message || 'Failed to replay job');
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleArchive = async (dlqId: string) => {
    setActionLoadingId(dlqId);
    try {
      await api.archiveDLQ(dlqId, 'Archived manually by operator');
      await fetchDLQ();
      onRefreshDLQ();
    } catch (err: any) {
      alert(err.message || 'Failed to archive DLQ entry');
    } finally {
      setActionLoadingId(null);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Header */}
      <div>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#fff' }}>Dead Letter Queue (DLQ)</h2>
        <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
          Review and replay tasks that failed permanently after exhausting all configured retry policies
        </p>
      </div>

      {/* DLQ Table */}
      <div className="glass-panel" style={{ overflow: 'hidden' }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>Job ID & Queue</th>
              <th>Resolution Status</th>
              <th>Attempts</th>
              <th>Failure Reason</th>
              <th>Failed At</th>
              <th style={{ textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={6} style={{ textAlign: 'center', padding: 30, color: 'var(--text-muted)' }}>
                  <RefreshCw size={18} className="animate-spin" style={{ display: 'inline', marginRight: 8 }} />
                  Loading DLQ entries...
                </td>
              </tr>
            ) : !pagedDLQ || pagedDLQ.content.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>
                  Dead Letter Queue is empty. All scheduled jobs are executing normally.
                </td>
              </tr>
            ) : (
              pagedDLQ.content.map((entry) => (
                <React.Fragment key={entry.id}>
                  <tr>
                    <td>
                      <div
                        style={{ fontWeight: 600, color: 'var(--accent-secondary)', cursor: 'pointer' }}
                        className="mono"
                        onClick={() => onSelectJob(entry.job_id)}
                      >
                        {entry.job_id}
                      </div>
                      <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }} className="mono">
                        DLQ: {entry.id.substring(0, 8)}...
                      </div>
                    </td>
                    <td>
                      <StatusBadge status={entry.resolution_status} />
                    </td>
                    <td>
                      <span style={{ fontWeight: 700, color: '#f87171' }}>
                        {entry.total_attempts} attempts
                      </span>
                    </td>
                    <td style={{ maxWidth: '300px' }}>
                      <div style={{ fontSize: '0.8125rem', color: '#fca5a5', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={entry.failure_reason}>
                        {entry.failure_reason}
                      </div>
                    </td>
                    <td>
                      <div style={{ fontSize: '0.75rem', color: '#fff' }}>
                        {new Date(entry.failed_at).toLocaleTimeString()}
                      </div>
                      <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }}>
                        {new Date(entry.failed_at).toLocaleDateString()}
                      </div>
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={() => onSelectJob(entry.job_id)}
                        >
                          <FileText size={13} /> Inspect
                        </button>
                        {entry.resolution_status === 'UNRESOLVED' && (
                          <>
                            <button
                              className="btn btn-primary btn-sm"
                              disabled={actionLoadingId === entry.id}
                              onClick={() => handleReplay(entry.id)}
                            >
                              <RotateCcw size={13} /> Replay
                            </button>
                            <button
                              className="btn btn-secondary btn-sm"
                              disabled={actionLoadingId === entry.id}
                              onClick={() => handleArchive(entry.id)}
                            >
                              <Archive size={13} /> Archive
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                  {entry.ai_root_cause_summary && (
                    <tr>
                      <td colSpan={6} style={{ padding: '0 24px 16px 24px', borderTop: 'none', background: 'var(--surface-light)' }}>
                        <div style={{ 
                          display: 'flex', 
                          gap: 14, 
                          alignItems: 'flex-start', 
                          padding: '16px',
                          background: 'linear-gradient(to right, rgba(99, 102, 241, 0.08), rgba(168, 85, 247, 0.03))',
                          borderRadius: '8px',
                          border: '1px solid rgba(99, 102, 241, 0.15)',
                        }}>
                          <div style={{ 
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            minWidth: 32, height: 32, borderRadius: '8px', background: 'rgba(99, 102, 241, 0.15)', color: '#818cf8', marginTop: 2
                          }}>
                            <Sparkles size={16} />
                          </div>
                          <div style={{ flex: 1 }}>
                            <div style={{ fontSize: '0.7rem', fontWeight: 700, color: '#818cf8', letterSpacing: '0.5px', marginBottom: 6 }}>
                              AI ROOT CAUSE ANALYSIS
                            </div>
                            <div style={{ fontSize: '0.875rem', color: '#e0e7ff', lineHeight: 1.6 }}>
                              {entry.ai_root_cause_summary}
                            </div>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))
            )}
          </tbody>
        </table>

        {/* Pagination Footer */}
        {pagedDLQ && pagedDLQ.totalPages > 1 && (
          <div style={{ padding: '14px 20px', borderTop: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
            <div>
              Showing {pagedDLQ.page * pagedDLQ.size + 1} - {Math.min((pagedDLQ.page + 1) * pagedDLQ.size, pagedDLQ.totalElements)} of {pagedDLQ.totalElements} entries
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                className="btn btn-secondary btn-sm"
                disabled={pagedDLQ.first}
                onClick={() => setPage(page - 1)}
              >
                <ChevronLeft size={14} /> Previous
              </button>
              <button
                className="btn btn-secondary btn-sm"
                disabled={pagedDLQ.last}
                onClick={() => setPage(page + 1)}
              >
                Next <ChevronRight size={14} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
