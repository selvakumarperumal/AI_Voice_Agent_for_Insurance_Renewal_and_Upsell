import { useState, useEffect } from 'react';
import api from '../api/client';
import StatusBadge from '../components/StatusBadge';

function Scheduler() {
    const [config, setConfig] = useState(null);
    const [stats, setStats] = useState(null);
    const [pendingCustomers, setPendingCustomers] = useState([]);
    const [scheduledCalls, setScheduledCalls] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [saving, setSaving] = useState(false);
    const [triggering, setTriggering] = useState(false);
    const [activeTab, setActiveTab] = useState('pending');

    // Form state for config
    const [formData, setFormData] = useState({
        enabled: true,
        daily_call_time: '10:00',
        days_before_expiry: 30,
        max_calls_per_day: 50,
        skip_if_called_within_days: 7
    });

    useEffect(() => {
        loadData();
    }, []);

    async function loadData() {
        try {
            setLoading(true);
            const [configData, statsData, pendingData, callsData] = await Promise.all([
                api.getSchedulerConfig(),
                api.getSchedulerStats(),
                api.getPendingCustomers({ days: 60, limit: 50 }),
                api.getScheduledCalls({ limit: 50 })
            ]);

            setConfig(configData);
            setStats(statsData);
            setPendingCustomers(pendingData.customers || []);
            setScheduledCalls(Array.isArray(callsData) ? callsData : []);

            setFormData({
                enabled: configData.enabled,
                daily_call_time: configData.daily_call_time,
                days_before_expiry: configData.days_before_expiry,
                max_calls_per_day: configData.max_calls_per_day,
                skip_if_called_within_days: configData.skip_if_called_within_days
            });
        } catch (err) {
            setError('Failed to load scheduler data');
            console.error(err);
        } finally {
            setLoading(false);
        }
    }

    async function handleSaveConfig(e) {
        e.preventDefault();
        try {
            setSaving(true);
            await api.updateSchedulerConfig(formData);
            await loadData();
        } catch (err) {
            alert('Failed to save: ' + err.message);
        } finally {
            setSaving(false);
        }
    }

    async function handleToggleScheduler() {
        try {
            setSaving(true);
            await api.updateSchedulerConfig({ enabled: !formData.enabled });
            await loadData();
        } catch (err) {
            alert('Failed to toggle: ' + err.message);
        } finally {
            setSaving(false);
        }
    }

    async function handleTriggerNow() {
        if (!confirm('Start calling customers with expiring policies now?')) return;

        try {
            setTriggering(true);
            const result = await api.triggerSchedulerNow({
                days: formData.days_before_expiry,
                max_calls: 20
            });

            if (result.success) {
                alert(`Scheduler triggered! Queued ${result.queued_count} calls.`);
                setTimeout(() => loadData(), 2000);
            } else {
                alert('Failed: ' + result.message);
            }
        } catch (err) {
            alert('Failed to trigger: ' + err.message);
        } finally {
            setTriggering(false);
        }
    }

    async function handleCancelCall(callId) {
        if (!confirm('Cancel this scheduled call?')) return;
        try {
            await api.cancelScheduledCall(callId);
            loadData();
        } catch (err) {
            alert('Failed to cancel: ' + err.message);
        }
    }

    async function handleScheduleCall(customerId) {
        try {
            const today = new Date().toISOString().split('T')[0];
            await api.scheduleCall({
                customer_id: customerId,
                scheduled_date: today,
                reason: 'manual'
            });
            loadData();
        } catch (err) {
            alert('Failed to schedule: ' + err.message);
        }
    }

    if (loading) {
        return <div className="loading"><div className="spinner"></div></div>;
    }

    return (
        <div className="scheduler-page">
            {/* Header */}
            <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                    <h1>📅 Call Scheduler</h1>
                    <p>Automate calls to customers with expiring policies</p>
                </div>
                <div style={{ display: 'flex', gap: '0.75rem' }}>
                    <button
                        className={`btn ${formData.enabled ? 'btn-danger' : 'btn-success'}`}
                        onClick={handleToggleScheduler}
                        disabled={saving}
                    >
                        {formData.enabled ? '⏸️ Pause Scheduler' : '▶️ Enable Scheduler'}
                    </button>
                    <button
                        className="btn btn-primary"
                        onClick={handleTriggerNow}
                        disabled={triggering}
                    >
                        {triggering ? '⏳ Running...' : '🚀 Run Now'}
                    </button>
                </div>
            </div>

            {error && (
                <div className="card" style={{ marginBottom: '1.5rem', background: 'rgba(239, 68, 68, 0.1)', borderColor: 'rgba(239, 68, 68, 0.3)' }}>
                    <p style={{ color: 'var(--error)', margin: 0 }}>⚠️ {error}</p>
                </div>
            )}

            {/* Status Banner */}
            <div
                className="card"
                style={{
                    marginBottom: '1.5rem',
                    background: formData.enabled
                        ? 'linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(16, 185, 129, 0.05) 100%)'
                        : 'linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(239, 68, 68, 0.05) 100%)',
                    borderColor: formData.enabled ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between'
                }}
            >
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    <div style={{
                        width: '48px',
                        height: '48px',
                        borderRadius: '12px',
                        background: formData.enabled ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '1.5rem'
                    }}>
                        {formData.enabled ? '✅' : '⏸️'}
                    </div>
                    <div>
                        <div style={{ fontSize: '1.1rem', fontWeight: '600', marginBottom: '0.25rem' }}>
                            {formData.enabled ? 'Scheduler Active' : 'Scheduler Paused'}
                        </div>
                        <div style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                            {formData.enabled
                                ? `Next run at ${stats?.next_scheduled_time || formData.daily_call_time} IST`
                                : 'Enable the scheduler to start auto-calling'}
                        </div>
                    </div>
                </div>
                <div style={{ display: 'flex', gap: '2rem', alignItems: 'center' }}>
                    <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: '1.5rem', fontWeight: '700', color: 'var(--success)' }}>
                            {stats?.completed_today || 0}
                        </div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Completed</div>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: '1.5rem', fontWeight: '700', color: 'var(--warning)' }}>
                            {stats?.pending_today || 0}
                        </div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Pending</div>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: '1.5rem', fontWeight: '700', color: 'var(--error)' }}>
                            {stats?.failed_today || 0}
                        </div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Failed</div>
                    </div>
                </div>
            </div>

            {/* Main Content Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: '340px 1fr', gap: '1.5rem' }}>

                {/* Left Side - Configuration */}
                <div className="card" style={{ height: 'fit-content' }}>
                    <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.75rem',
                        marginBottom: '1.5rem',
                        paddingBottom: '1rem',
                        borderBottom: '1px solid var(--border-color)'
                    }}>
                        <div style={{
                            width: '40px',
                            height: '40px',
                            background: 'var(--accent-gradient)',
                            borderRadius: '10px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: '1.25rem'
                        }}>⚙️</div>
                        <div>
                            <h3 style={{ margin: 0, fontSize: '1rem' }}>Configuration</h3>
                            <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                Customize scheduler behavior
                            </p>
                        </div>
                    </div>

                    <form onSubmit={handleSaveConfig}>
                        <div className="form-group">
                            <label className="form-label">Daily Call Time</label>
                            <input
                                type="time"
                                className="form-input"
                                value={formData.daily_call_time}
                                onChange={(e) => setFormData({ ...formData, daily_call_time: e.target.value })}
                            />
                        </div>

                        <div className="form-group">
                            <label className="form-label">Days Before Expiry</label>
                            <input
                                type="number"
                                className="form-input"
                                value={formData.days_before_expiry}
                                onChange={(e) => setFormData({ ...formData, days_before_expiry: parseInt(e.target.value) || 30 })}
                                min="1"
                                max="365"
                            />
                            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
                                Start calling this many days before policy expires
                            </p>
                        </div>

                        <div className="form-group">
                            <label className="form-label">Max Calls Per Day</label>
                            <input
                                type="number"
                                className="form-input"
                                value={formData.max_calls_per_day}
                                onChange={(e) => setFormData({ ...formData, max_calls_per_day: parseInt(e.target.value) || 50 })}
                                min="1"
                                max="200"
                            />
                        </div>

                        <div className="form-group">
                            <label className="form-label">Skip If Called Within (Days)</label>
                            <input
                                type="number"
                                className="form-input"
                                value={formData.skip_if_called_within_days}
                                onChange={(e) => setFormData({ ...formData, skip_if_called_within_days: parseInt(e.target.value) || 7 })}
                                min="1"
                                max="30"
                            />
                            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
                                Don't call customers contacted recently
                            </p>
                        </div>

                        <button
                            type="submit"
                            className="btn btn-primary"
                            style={{ width: '100%', marginTop: '0.5rem' }}
                            disabled={saving}
                        >
                            {saving ? 'Saving...' : '💾 Save Changes'}
                        </button>
                    </form>
                </div>

                {/* Right Side - Tabs */}
                <div>
                    {/* Tab Navigation */}
                    <div style={{
                        display: 'flex',
                        gap: '0.5rem',
                        marginBottom: '1rem',
                        background: 'var(--bg-card)',
                        padding: '0.5rem',
                        borderRadius: '12px',
                        border: '1px solid var(--border-color)'
                    }}>
                        <button
                            className={`btn ${activeTab === 'pending' ? 'btn-primary' : 'btn-secondary'}`}
                            onClick={() => setActiveTab('pending')}
                            style={{ flex: 1 }}
                        >
                            👥 Pending ({pendingCustomers.length})
                        </button>
                        <button
                            className={`btn ${activeTab === 'scheduled' ? 'btn-primary' : 'btn-secondary'}`}
                            onClick={() => setActiveTab('scheduled')}
                            style={{ flex: 1 }}
                        >
                            📋 Scheduled ({scheduledCalls.length})
                        </button>
                    </div>

                    {/* Tab Content */}
                    {activeTab === 'pending' && (
                        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
                            <div style={{
                                padding: '1rem 1.5rem',
                                borderBottom: '1px solid var(--border-color)',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between'
                            }}>
                                <div>
                                    <h3 style={{ margin: 0, fontSize: '1rem' }}>Customers to Call</h3>
                                    <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                        Policies expiring within {formData.days_before_expiry} days
                                    </p>
                                </div>
                                <span className="badge badge-warning">{pendingCustomers.length} pending</span>
                            </div>

                            <div style={{ maxHeight: '500px', overflowY: 'auto' }}>
                                {pendingCustomers.length === 0 ? (
                                    <div className="empty-state" style={{ padding: '3rem' }}>
                                        <div className="icon">✅</div>
                                        <h3>All caught up!</h3>
                                        <p>No customers need to be called right now</p>
                                    </div>
                                ) : (
                                    pendingCustomers.map((customer, index) => (
                                        <div
                                            key={customer.customer_id}
                                            style={{
                                                padding: '1rem 1.5rem',
                                                borderBottom: index < pendingCustomers.length - 1 ? '1px solid var(--border-color)' : 'none',
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: '1rem',
                                                transition: 'background 0.2s',
                                                cursor: 'default'
                                            }}
                                            onMouseEnter={(e) => e.currentTarget.style.background = 'var(--bg-glass)'}
                                            onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                                        >
                                            <div className="avatar" style={{
                                                background: customer.days_to_expiry <= 7
                                                    ? 'linear-gradient(135deg, #ef4444, #f97316)'
                                                    : customer.days_to_expiry <= 14
                                                        ? 'linear-gradient(135deg, #f59e0b, #eab308)'
                                                        : 'var(--accent-gradient)'
                                            }}>
                                                {customer.customer_name?.[0] || '?'}
                                            </div>
                                            <div style={{ flex: 1 }}>
                                                <div style={{ fontWeight: '500', marginBottom: '0.25rem' }}>
                                                    {customer.customer_name}
                                                </div>
                                                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                                    {customer.policy_name}
                                                </div>
                                            </div>
                                            <div style={{ textAlign: 'right', marginRight: '1rem' }}>
                                                <div style={{
                                                    fontWeight: '600',
                                                    color: customer.days_to_expiry <= 7
                                                        ? 'var(--error)'
                                                        : customer.days_to_expiry <= 14
                                                            ? 'var(--warning)'
                                                            : 'var(--text-secondary)'
                                                }}>
                                                    {customer.days_to_expiry} days
                                                </div>
                                                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                                    until expiry
                                                </div>
                                            </div>
                                            <button
                                                className="btn btn-sm btn-primary"
                                                onClick={() => handleScheduleCall(customer.customer_id)}
                                            >
                                                📞 Call
                                            </button>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>
                    )}

                    {activeTab === 'scheduled' && (
                        <div className="data-table-container">
                            <div className="data-table-header">
                                <div>
                                    <h3 style={{ margin: 0 }}>Scheduled Calls</h3>
                                    <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                        View and manage scheduled calls
                                    </p>
                                </div>
                                <span className="badge badge-info">{scheduledCalls.length} calls</span>
                            </div>
                            <table className="data-table">
                                <thead>
                                    <tr>
                                        <th>Customer</th>
                                        <th>Date</th>
                                        <th>Reason</th>
                                        <th>Status</th>
                                        <th>Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {scheduledCalls.length === 0 ? (
                                        <tr>
                                            <td colSpan="5">
                                                <div className="empty-state">
                                                    <div className="icon">📅</div>
                                                    <h3>No scheduled calls</h3>
                                                    <p>Calls will appear here when scheduled</p>
                                                </div>
                                            </td>
                                        </tr>
                                    ) : (
                                        scheduledCalls.map((call) => (
                                            <tr key={call.id}>
                                                <td>
                                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                                        <div className="avatar">{call.customer_name?.[0] || '?'}</div>
                                                        <div>
                                                            <div style={{ fontWeight: '500' }}>{call.customer_name || 'Unknown'}</div>
                                                            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                                                {call.customer_phone}
                                                            </div>
                                                        </div>
                                                    </div>
                                                </td>
                                                <td>
                                                    {new Date(call.scheduled_date).toLocaleDateString('en-IN', {
                                                        day: 'numeric',
                                                        month: 'short',
                                                        year: 'numeric'
                                                    })}
                                                </td>
                                                <td>
                                                    <span className="badge badge-default">
                                                        {call.reason.replace('_', ' ')}
                                                    </span>
                                                </td>
                                                <td>
                                                    <StatusBadge status={call.status} />
                                                </td>
                                                <td>
                                                    {(call.status === 'pending' || call.status === 'queued') && (
                                                        <button
                                                            className="btn btn-sm"
                                                            onClick={() => handleCancelCall(call.id)}
                                                            style={{
                                                                color: 'var(--error)',
                                                                background: 'rgba(239, 68, 68, 0.1)',
                                                                border: '1px solid rgba(239, 68, 68, 0.3)'
                                                            }}
                                                        >
                                                            ✕ Cancel
                                                        </button>
                                                    )}
                                                </td>
                                            </tr>
                                        ))
                                    )}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

export default Scheduler;
