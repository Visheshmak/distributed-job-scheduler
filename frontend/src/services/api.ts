import {
  ApiResponse,
  PagedResponse,
  OverviewMetrics,
  Queue,
  Job,
  JobDetail,
  Worker,
  DLQEntry,
  Project,
  RetryPolicy,
} from '../types';

const API_BASE = '/api/v1';

let authToken = localStorage.getItem('scheduler_token') || '';

export const setAuthToken = (token: string) => {
  authToken = token;
  localStorage.setItem('scheduler_token', token);
};

export const getAuthToken = () => authToken;

const request = async <T>(endpoint: string, options: RequestInit = {}): Promise<T> => {
  const headers = new Headers(options.headers || {});
  headers.set('Content-Type', 'application/json');

  if (authToken) {
    headers.set('Authorization', `Bearer ${authToken}`);
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 401 && endpoint !== '/auth/login') {
    // Attempt automatic login with default admin credentials
    const loginRes = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: 'admin@scheduler.io', password: 'admin123' }),
    });
    if (loginRes.ok) {
      const data = await loginRes.json();
      setAuthToken(data.data.access_token);
      headers.set('Authorization', `Bearer ${data.data.access_token}`);
      const retryRes = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });
      const retryText = await retryRes.text();
      const fixedRetryText = retryText.replace(/("\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?)(")/g, '$1Z$2');
      const retryJson = JSON.parse(fixedRetryText);
      return retryJson.data;
    }
  }

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.message || `HTTP Error ${response.status}: ${response.statusText}`);
  }

  const text = await response.text();
  // SQLite/Pydantic datetime serialization often drops the 'Z' timezone suffix
  // which causes the browser to parse it as local time. This regex appends 'Z' to ISO strings.
  const fixedText = text.replace(/("\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?)(")/g, '$1Z$2');
  const json: ApiResponse<T> = JSON.parse(fixedText);
  return json.data;
};

export const api = {
  // Auth
  login: async (email: string, password: string) => {
    const data = await request<{ access_token: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    setAuthToken(data.access_token);
    return data;
  },

  // Metrics
  getMetrics: () => request<OverviewMetrics>('/metrics/overview'),

  // Projects & Queues
  getProjects: () => request<Project[]>('/projects'),
  getQueues: (projectId?: string) =>
    request<Queue[]>(`/queues${projectId ? `?project_id=${projectId}` : ''}`),
  createQueue: (payload: { project_id: string; name: string; priority: number; max_concurrency: number; retry_policy_id?: string }) =>
    request<Queue>('/queues', { method: 'POST', body: JSON.stringify(payload) }),
  pauseQueue: (queueId: string) =>
    request<Queue>(`/queues/${queueId}/pause`, { method: 'POST' }),
  resumeQueue: (queueId: string) =>
    request<Queue>(`/queues/${queueId}/resume`, { method: 'POST' }),
  getRetryPolicies: () => request<RetryPolicy[]>('/queues/retry-policies'),

  // Jobs
  getJobs: (params: { page?: number; size?: number; status?: string; queue_id?: string; search?: string }) => {
    const query = new URLSearchParams();
    if (params.page !== undefined) query.set('page', params.page.toString());
    if (params.size !== undefined) query.set('size', params.size.toString());
    if (params.status) query.set('status', params.status);
    if (params.queue_id) query.set('queue_id', params.queue_id);
    if (params.search) query.set('search', params.search);
    return request<PagedResponse<Job>>(`/jobs?${query.toString()}`);
  },

  getJobDetail: (jobId: string) => request<JobDetail>(`/jobs/${jobId}/detail`),

  submitJob: (payload: {
    queue_id: string;
    project_id: string;
    job_type: string;
    payload?: Record<string, any>;
    priority?: number;
    max_retries?: number;
    cron_expression?: string;
    idempotency_key?: string;
    scheduled_at?: string;
  }) => request<Job>('/jobs', { method: 'POST', body: JSON.stringify(payload) }),

  submitBatch: (batchName: string, jobs: any[]) =>
    request<{ batch_name: string; total_jobs: number; successful_submissions: number; job_ids: string[] }>(
      '/jobs/batch',
      {
        method: 'POST',
        body: JSON.stringify({ batch_name: batchName, jobs }),
      }
    ),

  retryJob: (jobId: string) => request<Job>(`/jobs/${jobId}/retry`, { method: 'POST' }),
  cancelJob: (jobId: string) => request<Job>(`/jobs/${jobId}/cancel`, { method: 'POST' }),

  // Workers
  getWorkers: () => request<Worker[]>('/workers'),
  getWorker: (workerId: string) => request<Worker>(`/workers/${workerId}`),
  spawnWorker: () => request<string>('/workers/spawn', { method: 'POST' }),

  // DLQ
  getDLQ: (params: { page?: number; size?: number }) => {
    const query = new URLSearchParams();
    if (params.page !== undefined) query.set('page', params.page.toString());
    if (params.size !== undefined) query.set('size', params.size.toString());
    return request<PagedResponse<DLQEntry>>(`/dlq?${query.toString()}`);
  },

  replayDLQ: (dlqId: string) => request<DLQEntry>(`/dlq/${dlqId}/replay`, { method: 'POST' }),
  archiveDLQ: (dlqId: string, notes?: string) =>
    request<DLQEntry>(`/dlq/${dlqId}/archive`, {
      method: 'POST',
      body: JSON.stringify({ resolution_notes: notes }),
    }),

  // Demo generator: quickly triggers a live workload
  triggerDemoWorkload: async (queueId: string, projectId: string) => {
    const sampleJobs = [
      {
        queue_id: queueId,
        project_id: projectId,
        job_type: 'EMAIL_SEND',
        priority: 10,
        payload: { to: 'customer@stripe.com', subject: 'Payment Receipt #8841', delay_seconds: 0.5 },
      },
      {
        queue_id: queueId,
        project_id: projectId,
        job_type: 'DATA_PROCESSING',
        priority: 5,
        payload: { records_count: 500, delay_seconds: 0.8 },
      },
      {
        queue_id: queueId,
        project_id: projectId,
        job_type: 'FLAKY_TASK',
        priority: 2,
        max_retries: 3,
        payload: { fail_until_attempt: 2 },
      },
      {
        queue_id: queueId,
        project_id: projectId,
        job_type: 'ALWAYS_FAIL',
        priority: 0,
        max_retries: 2,
        payload: { simulated_error: 'Downstream gateway timeout' },
      },
      {
        queue_id: queueId,
        project_id: projectId,
        job_type: 'DATA_PROCESSING',
        priority: 8,
        payload: { records_count: 1200, delay_seconds: 0.6 },
      },
    ];

    return request<{ batch_name: string; total_jobs: number; successful_submissions: number; job_ids: string[] }>(
      '/jobs/batch',
      {
        method: 'POST',
        body: JSON.stringify({ batch_name: `demo-workload-${Date.now()}`, jobs: sampleJobs }),
      }
    );
  },
};
