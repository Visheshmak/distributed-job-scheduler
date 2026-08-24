import React, { useState, useEffect } from 'react';
import { Search, ChevronLeft, ChevronRight, RefreshCw } from 'lucide-react';
import { Job, Queue, PagedResponse } from '../types';
import { api } from '../services/api';
import { StatusBadge } from '../components/StatusBadge';

interface JobListProps {
  queues: Queue[];
  onSelectJob: (jobId: string) => void;
  refreshTrigger: number;
}

export const JobList: React.FC<JobListProps> = ({
  queues,
  onSelectJob,
  refreshTrigger,
}) => {
  const [pagedJobs, setPagedJobs] = useState<PagedResponse<Job> | null>(null);
  const [page, setPage] = useState(0);
  const [size] = useState(15);
  const [statusFilter, setStatusFilter] = useState('');
  const [queueFilter, setQueueFilter] = useState('');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(false);

  const fetchJobs = async () => {
    setLoading(true);
    try {
      const data = await api.getJobs({
        page,
        size,
        status: statusFilter || undefined,
        queue_id: queueFilter || undefined,
        search: search.trim() || undefined,
      });
      setPagedJobs(data);
    } catch (err) {
      console.error('Failed to fetch jobs', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, [page, statusFilter, queueFilter, refreshTrigger]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(0);
    fetchJobs();
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Header & Filter Controls */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 14 }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#fff' }}>Job Explorer</h2>
          <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
            Search, filter, and inspect execution audit trails for asynchronous jobs
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {/* Search Form */}
          <form onSubmit={handleSearchSubmit} style={{ display: 'flex', gap: 6 }}>
            <div style={{ position: 'relative' }}>
              <input
                type="text"
                className="form-input"
                placeholder="Search job type or key..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                style={{ paddingLeft: 32, width: '220px' }}
              />
              <Search size={14} style={{ position: 'absolute', left: 10, top: 11, color: 'var(--text-muted)' }} />
            </div>
            <button type="submit" className="btn btn-secondary btn-sm">
              Search
            </button>
          </form>

          {/* Status Filter */}
          <select
            className="form-input"
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(0);
            }}
            style={{ width: '150px' }}
          >
            <option value="">All Statuses</option>
            <option value="QUEUED">QUEUED</option>
            <option value="SCHEDULED">SCHEDULED</option>
            <option value="CLAIMED">CLAIMED</option>
            <option value="RUNNING">RUNNING</option>
            <option value="COMPLETED">COMPLETED</option>
            <option value="FAILED">FAILED</option>
            <option value="RETRY_PENDING">RETRY_PENDING</option>
            <option value="DEAD_LETTER">DEAD_LETTER</option>
            <option value="CANCELLED">CANCELLED</option>
          </select>

          {/* Queue Filter */}
          <select
            className="form-input"
            value={queueFilter}
            onChange={(e) => {
              setQueueFilter(e.target.value);
              setPage(0);
            }}
            style={{ width: '150px' }}
          >
            <option value="">All Queues</option>
            {queues.map((q) => (
              <option key={q.id} value={q.id}>
                {q.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Jobs Table */}
      <div className="glass-panel" style={{ overflow: 'hidden' }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>Job ID & Type</th>
              <th>Status</th>
              <th>Queue</th>
              <th>Priority</th>
              <th>Attempts</th>
              <th>Worker Node</th>
              <th>Created / Scheduled</th>
              <th style={{ textAlign: 'right' }}>Details</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={8} style={{ textAlign: 'center', padding: 30, color: 'var(--text-muted)' }}>
                  <RefreshCw size={18} className="animate-spin" style={{ display: 'inline', marginRight: 8 }} />
                  Loading jobs...
                </td>
              </tr>
            ) : !pagedJobs || pagedJobs.content.length === 0 ? (
              <tr>
                <td colSpan={8} style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>
                  No jobs found matching criteria.
                </td>
              </tr>
            ) : (
              pagedJobs.content.map((job) => {
                const queueObj = queues.find((q) => q.id === job.queue_id);
                return (
                  <tr
                    key={job.id}
                    onClick={() => onSelectJob(job.id)}
                    style={{ cursor: 'pointer' }}
                  >
                    <td>
                      <div style={{ fontWeight: 600, color: '#fff' }}>{job.job_type}</div>
                      <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }} className="mono">
                        {job.id}
                      </div>
                      {job.idempotency_key && (
                        <div style={{ fontSize: '0.6875rem', color: 'var(--accent-secondary)' }} className="mono">
                          key: {job.idempotency_key}
                        </div>
                      )}
                    </td>
                    <td>
                      <StatusBadge status={job.status} />
                    </td>
                    <td>
                      <span style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
                        {queueObj?.name || 'default'}
                      </span>
                    </td>
                    <td>
                      <span className="badge" style={{ background: 'rgba(255,255,255,0.06)', color: '#fff' }}>
                        {job.priority}
                      </span>
                    </td>
                    <td>
                      <span style={{ fontWeight: 600 }}>
                        {job.attempt_count} / {job.max_retries}
                      </span>
                    </td>
                    <td>
                      <span style={{ fontSize: '0.75rem', color: job.claimed_by_worker_id ? 'var(--accent-secondary)' : 'var(--text-muted)' }} className="mono">
                        {job.claimed_by_worker_id || '—'}
                      </span>
                    </td>
                    <td>
                      <div style={{ fontSize: '0.75rem', color: '#fff' }}>
                        {new Date(job.created_at).toLocaleTimeString()}
                      </div>
                      <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }}>
                        {new Date(job.created_at).toLocaleDateString()}
                      </div>
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectJob(job.id);
                        }}
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>

        {/* Pagination Footer */}
        {pagedJobs && pagedJobs.totalPages > 1 && (
          <div style={{ padding: '14px 20px', borderTop: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
            <div>
              Showing {pagedJobs.page * pagedJobs.size + 1} - {Math.min((pagedJobs.page + 1) * pagedJobs.size, pagedJobs.totalElements)} of {pagedJobs.totalElements} jobs
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                className="btn btn-secondary btn-sm"
                disabled={pagedJobs.first}
                onClick={() => setPage(page - 1)}
              >
                <ChevronLeft size={14} /> Previous
              </button>
              <span style={{ padding: '4px 10px', background: 'rgba(255,255,255,0.05)', borderRadius: 6 }}>
                Page {page + 1} of {pagedJobs.totalPages}
              </span>
              <button
                className="btn btn-secondary btn-sm"
                disabled={pagedJobs.last}
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
