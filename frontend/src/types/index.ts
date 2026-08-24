export type JobStatus =
  | 'QUEUED'
  | 'SCHEDULED'
  | 'CLAIMED'
  | 'RUNNING'
  | 'COMPLETED'
  | 'FAILED'
  | 'RETRY_PENDING'
  | 'CANCELLED'
  | 'DEAD_LETTER';

export type ExecutionStatus = 'RUNNING' | 'COMPLETED' | 'FAILED' | 'TIMED_OUT';

export type QueueStatus = 'ACTIVE' | 'PAUSED';

export type WorkerStatus = 'STARTING' | 'IDLE' | 'BUSY' | 'STOPPING' | 'STOPPED' | 'UNHEALTHY';

export type RetryStrategy = 'FIXED' | 'LINEAR' | 'EXPONENTIAL';

export type DLQResolutionStatus = 'UNRESOLVED' | 'REPLAYED' | 'ARCHIVED';

export interface RetryPolicy {
  id: string;
  name: string;
  strategy: RetryStrategy;
  max_attempts: number;
  base_delay_ms: number;
  max_delay_ms: number;
  jitter_factor: number;
  created_at: string;
}

export interface Queue {
  id: string;
  project_id: string;
  retry_policy_id?: string;
  name: string;
  priority: number;
  max_concurrency: number;
  status: QueueStatus;
  created_at: string;
  updated_at: string;
  retry_policy?: RetryPolicy;
  queued_count: number;
  running_count: number;
  completed_count: number;
  failed_count: number;
}

export interface Job {
  id: string;
  queue_id: string;
  project_id: string;
  idempotency_key?: string;
  job_type: string;
  priority: number;
  status: JobStatus;
  scheduled_at: string;
  cron_expression?: string;
  attempt_count: number;
  max_retries: number;
  timeout_seconds: number;
  claimed_by_worker_id?: string;
  claimed_at?: string;
  started_at?: string;
  completed_at?: string;
  failed_at?: string;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

export interface JobLog {
  id: number;
  execution_id: string;
  log_level: string;
  message: string;
  timestamp: string;
}

export interface JobExecution {
  id: string;
  job_id: string;
  attempt_number: number;
  worker_id: string;
  status: ExecutionStatus;
  started_at: string;
  finished_at?: string;
  duration_ms?: number;
  error_message?: string;
  stack_trace?: string;
  logs?: JobLog[];
}

export interface JobTimelineItem {
  timestamp: string;
  event: string;
  status: string;
  worker_id?: string;
  attempt_number?: number;
  details?: string;
}

export interface JobDetail extends Job {
  payload: Record<string, any>;
  executions: JobExecution[];
  timeline: JobTimelineItem[];
}

export interface Worker {
  worker_id: string;
  hostname: string;
  status: WorkerStatus;
  concurrency: number;
  current_running_jobs: number;
  last_heartbeat_at: string;
  started_at: string;
  metadata_json?: Record<string, any>;
  is_healthy: boolean;
  uptime_seconds?: number;
}

export interface DLQEntry {
  id: string;
  job_id: string;
  queue_id: string;
  failed_at: string;
  failure_reason: string;
  final_exception?: string;
  total_attempts: number;
  worker_id?: string;
  resolved_at?: string;
  resolution_status: DLQResolutionStatus;
  resolution_notes?: string;
  ai_root_cause_summary?: string;
  created_at: string;
}

export interface QueueDepthMetric {
  queue_id: string;
  queue_name: string;
  queued_count: number;
  running_count: number;
}

export interface SystemThroughputMetric {
  timestamp: string;
  completed_count: number;
  failed_count: number;
}

export interface OverviewMetrics {
  total_jobs: number;
  queued_jobs: number;
  running_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  dlq_jobs: number;
  active_workers: number;
  total_workers: number;
  system_load_pct: number;
  queues: QueueDepthMetric[];
  throughput_history: SystemThroughputMetric[];
}

export interface Project {
  id: string;
  organization_id: string;
  name: string;
  slug: string;
  description?: string;
  created_at: string;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  created_at: string;
}

export interface ApiResponse<T> {
  success: boolean;
  message?: string;
  data: T;
  timestamp: string;
  requestId?: string;
}

export interface PagedResponse<T> {
  content: T[];
  page: number;
  size: number;
  totalElements: number;
  totalPages: number;
  last: boolean;
  first: boolean;
}
