import React, { useState, useEffect, useCallback } from 'react';
import { Navbar } from './components/Navbar';
import { NewJobForm } from './components/NewJobForm';
import { JobDetails } from './components/JobDetails';
import { Home } from './pages/Home';
import { QueueList } from './pages/QueueList';
import { JobList } from './pages/JobList';
import { WorkerList } from './pages/WorkerList';
import { FailedJobs } from './pages/FailedJobs';
import { OverviewMetrics, Queue, Job, Worker, Project, RetryPolicy } from './types';
import { api } from './services/api';

export function App() {
  console.log("App rendered - why does this fire twice in dev?? oh right, React StrictMode");
  
  const [activeTab, setActiveTab] = useState('overview');
  const [metrics, setMetrics] = useState<OverviewMetrics | null>(null);
  const [queues, setQueues] = useState<Queue[]>([]);
  const [recentJobs, setRecentJobs] = useState<Job[]>([]);
  const [workers, setWorkers] = useState<Worker[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [retryPolicies, setRetryPolicies] = useState<RetryPolicy[]>([]);
  
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [isSubmitModalOpen, setIsSubmitModalOpen] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [refreshInterval, setRefreshInterval] = useState<number>(3000);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  const loadData = useCallback(async () => {
    setIsRefreshing(true);
    try {
      const [m, q, w, jRes, p, rp] = await Promise.all([
        api.getMetrics().catch(() => null),
        api.getQueues().catch(() => []),
        api.getWorkers().catch(() => []),
        api.getJobs({ page: 0, size: 10 }).catch(() => null),
        api.getProjects().catch(() => []),
        api.getRetryPolicies().catch(() => []),
      ]);

      if (m) setMetrics(m);
      if (q) setQueues(q);
      if (w) setWorkers(w);
      if (jRes) setRecentJobs(jRes.content);
      if (p) setProjects(p);
      if (rp) setRetryPolicies(rp);
    } catch (err) {
      console.error('Error fetching dashboard telemetry', err);
    } finally {
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData, refreshTrigger]);

  // WebSocket connection for live overview metrics
  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/api/v1/ws/dashboard');
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data && data.success && data.data) {
          setMetrics(data.data);
        }
      } catch (err) {
        console.error('WebSocket parse error:', err);
      }
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    // Polling fallback for other entities (jobs, queues, etc.)
    const interval = setInterval(() => {
      api.getQueues().then(setQueues).catch(console.error);
      api.getWorkers().then(setWorkers).catch(console.error);
      api.getJobs({ page: 0, size: 10 }).then(res => setRecentJobs(res.content)).catch(console.error);
    }, refreshInterval || 3000);
    
    return () => {
      ws.close();
      clearInterval(interval);
    };
  }, [refreshInterval]);

  const handleTriggerDemo = async () => {
    const targetQueueId = queues[0]?.id;
    const targetProjectId = projects[0]?.id;
    if (!targetQueueId || !targetProjectId) {
      showToast('No active queues available to receive demo workload.');
      return;
    }

    try {
      const res = await api.triggerDemoWorkload(targetQueueId, targetProjectId);
      showToast(`Injected 5 demo workloads! (Batch: ${res.batch_name})`);
      setRefreshTrigger((prev) => prev + 1);
    } catch (err: any) {
      showToast(`Demo injection failed: ${err.message}`);
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Toast Notification */}
      {toastMessage && (
        <div
          style={{
            position: 'fixed',
            bottom: 24,
            right: 24,
            zIndex: 100,
            background: 'linear-gradient(135deg, #4f46e5, #06b6d4)',
            color: '#fff',
            padding: '12px 20px',
            borderRadius: 10,
            boxShadow: '0 10px 25px rgba(0,0,0,0.5)',
            fontSize: '0.875rem',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            animation: 'fadeIn 0.3s ease',
          }}
        >
          {toastMessage}
        </div>
      )}

      {/* Top Navbar */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        dlqCount={metrics?.dlq_jobs || 0}
        activeWorkers={metrics?.active_workers || 0}
        onOpenSubmitModal={() => setIsSubmitModalOpen(true)}
        onTriggerDemo={handleTriggerDemo}
        onRefresh={() => setRefreshTrigger((prev) => prev + 1)}
        isRefreshing={isRefreshing}
        refreshInterval={refreshInterval}
        setRefreshInterval={setRefreshInterval}
      />

      {/* Main Content Area */}
      <main style={{ flex: 1, maxWidth: '1440px', width: '100%', margin: '0 auto', padding: '24px' }}>
        {activeTab === 'overview' && (
          <Home
            metrics={metrics}
            queues={queues}
            recentJobs={recentJobs}
            onSelectJob={(id) => setSelectedJobId(id)}
            onNavigateTab={(tab) => setActiveTab(tab)}
          />
        )}

        {activeTab === 'queues' && (
          <QueueList
            queues={queues}
            projects={projects}
            retryPolicies={retryPolicies}
            onRefresh={() => setRefreshTrigger((prev) => prev + 1)}
          />
        )}

        {activeTab === 'jobs' && (
          <JobList
            queues={queues}
            onSelectJob={(id) => setSelectedJobId(id)}
            refreshTrigger={refreshTrigger}
          />
        )}

        {activeTab === 'workers' && <WorkerList workers={workers} />}

        {activeTab === 'dlq' && (
          <FailedJobs
            onSelectJob={(id) => setSelectedJobId(id)}
            onRefreshDLQ={() => setRefreshTrigger((prev) => prev + 1)}
            refreshTrigger={refreshTrigger}
          />
        )}
      </main>

      {/* Slide-over Inspection Drawer */}
      <JobDetails
        jobId={selectedJobId}
        onClose={() => setSelectedJobId(null)}
        onJobActionSuccess={() => setRefreshTrigger((prev) => prev + 1)}
      />

      {/* Submit Job Modal */}
      <NewJobForm
        isOpen={isSubmitModalOpen}
        onClose={() => setIsSubmitModalOpen(false)}
        queues={queues}
        projects={projects}
        onJobSubmitted={() => {
          showToast('Job successfully submitted to queue!');
          setRefreshTrigger((prev) => prev + 1);
        }}
      />
    </div>
  );
}

export default App;
