import React, { ReactNode } from 'react';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: ReactNode;
  trend?: string;
  trendPositive?: boolean;
  glowColor?: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  trend,
  trendPositive,
  glowColor = 'rgba(99, 102, 241, 0.15)',
}) => {
  return (
    <div
      className="glass-panel"
      style={{
        padding: '20px 24px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          position: 'absolute',
          top: '-20px',
          right: '-20px',
          width: '80px',
          height: '80px',
          background: glowColor,
          borderRadius: '50%',
          filter: 'blur(30px)',
          pointerEvents: 'none',
        }}
      />
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
        <span style={{ fontSize: '0.875rem', fontWeight: 500, color: 'var(--text-secondary)' }}>{title}</span>
        <div style={{ padding: 8, borderRadius: 8, background: 'rgba(255, 255, 255, 0.05)', color: 'var(--accent-secondary)' }}>
          {icon}
        </div>
      </div>
      <div>
        <div style={{ fontSize: '1.875rem', fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '-0.02em' }}>
          {value}
        </div>
        {(subtitle || trend) && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 4, fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            {trend && (
              <span style={{ color: trendPositive ? '#34d399' : '#f87171', fontWeight: 600 }}>
                {trend}
              </span>
            )}
            {subtitle && <span>{subtitle}</span>}
          </div>
        )}
      </div>
    </div>
  );
};
