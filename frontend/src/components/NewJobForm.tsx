import React, { useState } from 'react';
import { X, Send } from 'lucide-react';
import { Queue, Project } from '../types';
import { api } from '../services/api';

interface NewJobFormProps {
  isOpen: boolean;
  onClose: () => void;
  queues: Queue[];
  projects: Project[];
  onJobSubmitted: () => void;
}

export const NewJobForm: React.FC<NewJobFormProps> = ({
  isOpen,
  onClose,
  queues,
  projects,
  onJobSubmitted,
}) => {
  const [tab, setTab] = useState<'single' | 'batch'>('single');
  const [selectedQueueId, setSelectedQueueId] = useState(queues[0]?.id || '');
  const [jobType, setJobType] = useState('EMAIL_SEND');
  const [payloadText, setPayloadText] = useState('{\n  "to": "user@example.com",\n  "subject": "System Alert"\n}');
  const [priority, setPriority] = useState(0);
  const [maxRetries, setMaxRetries] = useState(3);
  const [idempotencyKey, setIdempotencyKey] = useState('');
  const [delaySeconds, setDelaySeconds] = useState(0);
  const [cronExpression, setCronExpression] = useState('');
  
  // Batch
  const [batchName, setBatchName] = useState('bulk-analytics-batch');
  const [batchCount, setBatchCount] = useState(10);
  const [batchJobType, setBatchJobType] = useState('RANDOM_MIX');
  
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  if (!isOpen) return null;

  const defaultProjectId = projects[0]?.id || (queues.find(q => q.id === selectedQueueId)?.project_id) || '';

  const handleSubmitSingle = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrorMsg('');

    try {
      let parsedPayload = {};
      if (payloadText.trim()) {
        parsedPayload = JSON.parse(payloadText);
      }

      let scheduledAt: string | undefined = undefined;
      if (delaySeconds > 0) {
        const d = new Date(Date.now() + delaySeconds * 1000);
        scheduledAt = d.toISOString();
      }

      await api.submitJob({
        queue_id: selectedQueueId || queues[0]?.id,
        project_id: defaultProjectId,
        job_type: jobType,
        payload: parsedPayload,
        priority: Number(priority),
        max_retries: Number(maxRetries),
        idempotency_key: idempotencyKey.trim() || undefined,
        cron_expression: cronExpression.trim() || undefined,
        scheduled_at: scheduledAt,
      });

      onJobSubmitted();
      onClose();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to submit job');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSubmitBatch = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrorMsg('');

    try {
      const qId = selectedQueueId || queues[0]?.id;
      const possibleTypes = ['EMAIL_SEND', 'DATA_PROCESSING', 'FLAKY_TASK', 'ALWAYS_FAIL'];
      const batchJobs = Array.from({ length: batchCount }, (_, i) => {
        const typeToUse = batchJobType === 'RANDOM_MIX' 
          ? possibleTypes[Math.floor(Math.random() * possibleTypes.length)] 
          : batchJobType;
          
        return {
          queue_id: qId,
          project_id: defaultProjectId,
          job_type: typeToUse,
          priority: 5,
          payload: { item_index: i + 1, batch: batchName, delay_seconds: 0.4 },
        };
      });

      await api.submitBatch(batchName, batchJobs);
      onJobSubmitted();
      onClose();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to submit batch');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      className="animate-fade-in"
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.75)',
        backdropFilter: 'blur(6px)',
        zIndex: 50,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 16,
      }}
      onClick={onClose}
    >
      <div
        className="glass-panel animate-pop-in"
        style={{
          width: '100%',
          maxWidth: '560px',
          background: 'var(--bg-modal)',
          border: '1px solid rgba(255, 255, 255, 0.15)',
          borderRadius: 16,
          boxShadow: '0 20px 40px rgba(0,0,0,0.6)',
          overflow: 'hidden',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 24px', borderBottom: '1px solid var(--border-subtle)' }}>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <div style={{ padding: 6, borderRadius: 8, background: 'rgba(99, 102, 241, 0.2)', color: 'var(--accent-primary)' }}>
              <Send size={18} />
            </div>
            <div>
              <h3 style={{ fontSize: '1.125rem', fontWeight: 700, color: '#fff' }}>Submit New Job</h3>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Dispatch tasks to distributed workers</p>
            </div>
          </div>
          <button onClick={onClose} style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
            <X size={20} />
          </button>
        </div>

        {/* Mode Switcher */}
        <div style={{ display: 'flex', borderBottom: '1px solid var(--border-subtle)', background: 'rgba(0,0,0,0.2)' }}>
          <button
            onClick={() => setTab('single')}
            style={{
              flex: 1,
              padding: '10px 16px',
              border: 'none',
              background: tab === 'single' ? 'rgba(99, 102, 241, 0.15)' : 'transparent',
              borderBottom: tab === 'single' ? '2px solid var(--accent-primary)' : 'none',
              color: tab === 'single' ? '#fff' : 'var(--text-secondary)',
              fontWeight: 600,
              fontSize: '0.875rem',
              cursor: 'pointer',
            }}
          >
            Single Job
          </button>
          <button
            onClick={() => setTab('batch')}
            style={{
              flex: 1,
              padding: '10px 16px',
              border: 'none',
              background: tab === 'batch' ? 'rgba(99, 102, 241, 0.15)' : 'transparent',
              borderBottom: tab === 'batch' ? '2px solid var(--accent-primary)' : 'none',
              color: tab === 'batch' ? '#fff' : 'var(--text-secondary)',
              fontWeight: 600,
              fontSize: '0.875rem',
              cursor: 'pointer',
            }}
          >
            Batch Ingestion
          </button>
        </div>

        {errorMsg && (
          <div style={{ margin: '16px 24px 0', padding: '10px 14px', borderRadius: 8, background: 'rgba(239, 68, 68, 0.15)', border: '1px solid rgba(239, 68, 68, 0.3)', color: '#fca5a5', fontSize: '0.8125rem' }}>
            {errorMsg}
          </div>
        )}

        {tab === 'single' ? (
          <form onSubmit={handleSubmitSingle} style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div>
                <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4, display: 'block' }}>Target Queue</label>
                <select
                  className="form-input"
                  value={selectedQueueId}
                  onChange={(e) => setSelectedQueueId(e.target.value)}
                  required
                >
                  {queues.map((q) => (
                    <option key={q.id} value={q.id}>
                      {q.name} (Priority: {q.priority})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4, display: 'block' }}>Job Type</label>
                <select
                  className="form-input"
                  value={jobType}
                  onChange={(e) => setJobType(e.target.value)}
                >
                  <option value="EMAIL_SEND">EMAIL_SEND</option>
                  <option value="DATA_PROCESSING">DATA_PROCESSING</option>
                  <option value="FLAKY_TASK">FLAKY_TASK (Simulated Retry)</option>
                  <option value="ALWAYS_FAIL">ALWAYS_FAIL (Simulated DLQ)</option>
                </select>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
              <div>
                <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4, display: 'block' }}>Priority</label>
                <input
                  type="number"
                  className="form-input"
                  value={priority}
                  onChange={(e) => setPriority(Number(e.target.value))}
                  min={-10}
                  max={10}
                />
              </div>
              <div>
                <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4, display: 'block' }}>Max Retries</label>
                <input
                  type="number"
                  className="form-input"
                  value={maxRetries}
                  onChange={(e) => setMaxRetries(Number(e.target.value))}
                  min={0}
                  max={5}
                />
              </div>
              <div>
                <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4, display: 'block' }}>Delay (Seconds)</label>
                <input
                  type="number"
                  className="form-input"
                  value={delaySeconds}
                  onChange={(e) => setDelaySeconds(Number(e.target.value))}
                  min={0}
                  placeholder="0 (Immediate)"
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div>
                <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4, display: 'block' }}>Idempotency Key (Optional)</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. invoice-9921"
                  value={idempotencyKey}
                  onChange={(e) => setIdempotencyKey(e.target.value)}
                />
              </div>
              <div>
                <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4, display: 'block' }}>Cron Expression (Optional)</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. */5 * * * *"
                  value={cronExpression}
                  onChange={(e) => setCronExpression(e.target.value)}
                />
              </div>
            </div>

            <div>
              <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4, display: 'block' }}>Payload (JSON)</label>
              <textarea
                className="form-input mono"
                rows={3}
                value={payloadText}
                onChange={(e) => setPayloadText(e.target.value)}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 8 }}>
              <button type="button" className="btn btn-secondary" onClick={onClose}>
                Cancel
              </button>
              <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
                {isSubmitting ? 'Submitting...' : 'Dispatch Job'}
              </button>
            </div>
          </form>
        ) : (
          <form onSubmit={handleSubmitBatch} style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div>
                <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4, display: 'block' }}>Target Queue</label>
                <select
                  className="form-input"
                  value={selectedQueueId}
                  onChange={(e) => setSelectedQueueId(e.target.value)}
                  required
                >
                  {queues.map((q) => (
                    <option key={q.id} value={q.id}>
                      {q.name}
                    </option>
                  ))}
                </select>
              </div>
              
              <div>
                <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4, display: 'block' }}>Job Type</label>
                <select
                  className="form-input"
                  value={batchJobType}
                  onChange={(e) => setBatchJobType(e.target.value)}
                >
                  <option value="RANDOM_MIX">RANDOM_MIX (Mixed Workload)</option>
                  <option value="EMAIL_SEND">EMAIL_SEND</option>
                  <option value="DATA_PROCESSING">DATA_PROCESSING</option>
                  <option value="FLAKY_TASK">FLAKY_TASK</option>
                  <option value="ALWAYS_FAIL">ALWAYS_FAIL</option>
                </select>
              </div>
            </div>

            <div>
              <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4, display: 'block' }}>Batch Identifier</label>
              <input
                type="text"
                className="form-input"
                value={batchName}
                onChange={(e) => setBatchName(e.target.value)}
                required
              />
            </div>

            <div>
              <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4, display: 'block' }}>
                Batch Job Count: <strong style={{ color: 'var(--accent-secondary)' }}>{batchCount}</strong>
              </label>
              <input
                type="range"
                min={5}
                max={50}
                value={batchCount}
                onChange={(e) => setBatchCount(Number(e.target.value))}
                style={{ width: '100%', accentColor: 'var(--accent-primary)' }}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 8 }}>
              <button type="button" className="btn btn-secondary" onClick={onClose}>
                Cancel
              </button>
              <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
                {isSubmitting ? 'Ingesting...' : `Submit ${batchCount} Jobs Batch`}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
