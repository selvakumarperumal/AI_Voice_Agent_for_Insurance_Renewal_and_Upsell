import { useState, useEffect } from 'react';
import api from '../api/client';
import StatsCard from '../components/StatsCard';
import StatusBadge from '../components/StatusBadge';

function Dashboard() {
    const [stats, setStats] = useState(null);
    const [conversion, setConversion] = useState(null);
    const [recentCalls, setRecentCalls] = useState([]);
    const [expiringPolicies, setExpiringPolicies] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        loadDashboardData();
    }, []);

    async function loadDashboardData() {
        try {
            setLoading(true);
            setError(null);

            const [statsData, conversionData, callsData, policiesData] = await Promise.all([
                api.getCallSummary(30).catch(() => null),
                api.getConversionRate(30).catch(() => null),
                api.getCalls({ limit: 5 }).catch(() => []),
                api.getExpiringPolicies(30).catch(() => []),
            ]);

            setStats(statsData);
            setConversion(conversionData);
            setRecentCalls(Array.isArray(callsData) ? callsData.slice(0, 5) : []);
            setExpiringPolicies(Array.isArray(policiesData) ? policiesData.slice(0, 5) : []);
        } catch (err) {
            setError('Failed to load dashboard data. Make sure the backend is running.');
            console.error(err);
        } finally {
            setLoading(false);
        }
    }

    if (loading) {
        return (
            <div className="loading">
                <div className="spinner"></div>
            </div>
        );
    }

    return (
        <div>
            <div className="page-header">
                <h1>Dashboard</h1>
                <p>AI Voice Agent Overview & Analytics</p>
            </div>

            {error && (
                <div className="card" style={{ marginBottom: '1.5rem', background: 'rgba(239, 68, 68, 0.1)', borderColor: 'var(--error)' }}>
                    <p style={{ color: 'var(--error)' }}>⚠️ {error}</p>
                    <button className="btn btn-secondary" style={{ marginTop: '0.5rem' }} onClick={loadDashboardData}>
                        Retry
                    </button>
                </div>
            )}

            {/* Stats Grid */}
            <div className="stats-grid">
                <StatsCard
                    icon="📞"
                    value={stats?.total_calls || 0}
                    label="Total Calls (30 days)"
                    change={`${stats?.success_rate || 0}% success rate`}
                />
                <StatsCard
                    icon="✅"
                    value={stats?.completed_calls || 0}
                    label="Completed Calls"
                    change={`${(stats?.average_duration_seconds / 60).toFixed(1) || 0} min avg`}
                />
                <StatsCard
                    icon="🎯"
                    value={`${conversion?.renewal_conversion_rate || 0}%`}
                    label="Renewal Conversion"
                    change={`${conversion?.counts?.interested || 0} interested`}
                />
                <StatsCard
                    icon="📈"
                    value={`${conversion?.upsell_conversion_rate || 0}%`}
                    label="Upsell Rate"
                    change={`${conversion?.counts?.upsell_accepted || 0} accepted`}
                />
            </div>

            {/* Two Column Layout */}
            <div className="grid-2">
                {/* Recent Calls */}
                <div className="data-table-container">
                    <div className="data-table-header">
                        <h2>📞 Recent Calls</h2>
                    </div>
                    {recentCalls.length === 0 ? (
                        <div className="empty-state">
                            <div className="icon">📞</div>
                            <h3>No calls yet</h3>
                            <p>Start making AI calls to see data here</p>
                        </div>
                    ) : (
                        <table className="data-table">
                            <thead>
                                <tr>
                                    <th>Customer</th>
                                    <th>Status</th>
                                    <th>Outcome</th>
                                </tr>
                            </thead>
                            <tbody>
                                {recentCalls.map((call) => (
                                    <tr key={call.id}>
                                        <td>
                                            <div className="font-medium">{call.customer_name || 'Unknown'}</div>
                                            <div className="text-muted text-sm">{call.customer_phone || '-'}</div>
                                        </td>
                                        <td>
                                            <StatusBadge status={call.status} />
                                        </td>
                                        <td>
                                            {call.outcome ? (
                                                <StatusBadge status={call.outcome} />
                                            ) : (
                                                <span className="text-muted">-</span>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>

                {/* Expiring Policies */}
                <div className="data-table-container">
                    <div className="data-table-header">
                        <h2>⏰ Expiring Soon</h2>
                    </div>
                    {expiringPolicies.length === 0 ? (
                        <div className="empty-state">
                            <div className="icon">📋</div>
                            <h3>No expiring policies</h3>
                            <p>All policies are in good standing</p>
                        </div>
                    ) : (
                        <table className="data-table">
                            <thead>
                                <tr>
                                    <th>Policy</th>
                                    <th>Customer</th>
                                    <th>Expires</th>
                                </tr>
                            </thead>
                            <tbody>
                                {expiringPolicies.map((policy) => (
                                    <tr key={policy.id}>
                                        <td>
                                            <div className="font-medium">{policy.policy_number}</div>
                                            <div className="text-muted text-sm">{policy.product_name || 'N/A'}</div>
                                        </td>
                                        <td>{policy.customer_name || 'Unknown'}</td>
                                        <td>
                                            <StatusBadge status="expiring" />
                                            <div className="text-muted text-sm" style={{ marginTop: '4px' }}>
                                                {new Date(policy.end_date).toLocaleDateString()}
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>
            </div>

            {/* Call Outcomes Chart (Simple bar representation) */}
            {conversion?.counts && Object.keys(conversion.counts).length > 0 && (
                <div className="chart-container" style={{ marginTop: 'var(--spacing-lg)' }}>
                    <div className="chart-header">
                        <h3>📊 Call Outcomes Distribution</h3>
                    </div>
                    <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                        {Object.entries(conversion.counts).map(([outcome, count]) => (
                            <div key={outcome} style={{ flex: 1, minWidth: '150px' }}>
                                <div className="flex justify-between items-center" style={{ marginBottom: '0.5rem' }}>
                                    <span className="text-sm">{outcome.replace('_', ' ')}</span>
                                    <span className="font-bold">{count}</span>
                                </div>
                                <div style={{
                                    height: '8px',
                                    background: 'var(--bg-glass)',
                                    borderRadius: '4px',
                                    overflow: 'hidden'
                                }}>
                                    <div style={{
                                        width: `${Math.min((count / (conversion.completed_calls || 1)) * 100, 100)}%`,
                                        height: '100%',
                                        background: 'var(--accent-gradient)',
                                        borderRadius: '4px',
                                        transition: 'width 0.5s ease'
                                    }} />
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

export default Dashboard;
