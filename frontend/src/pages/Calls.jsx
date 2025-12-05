import { useState, useEffect } from 'react';
import api from '../api/client';
import StatusBadge from '../components/StatusBadge';

function Calls() {
    const [calls, setCalls] = useState([]);
    const [customers, setCustomers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [search, setSearch] = useState('');
    const [statusFilter, setStatusFilter] = useState('');
    const [selectedCustomers, setSelectedCustomers] = useState([]);
    const [showBatchModal, setShowBatchModal] = useState(false);
    const [batchLoading, setBatchLoading] = useState(false);

    useEffect(() => {
        loadData();
    }, [statusFilter]);

    async function loadData() {
        try {
            setLoading(true);
            const params = {};
            if (statusFilter) params.status = statusFilter;

            const [callsData, customersData] = await Promise.all([
                api.getCalls(params),
                api.getCustomers()
            ]);

            setCalls(Array.isArray(callsData) ? callsData : []);
            setCustomers(Array.isArray(customersData) ? customersData : []);
        } catch (err) {
            setError('Failed to load data');
            console.error(err);
        } finally {
            setLoading(false);
        }
    }

    async function handleBatchCall() {
        if (selectedCustomers.length === 0) {
            alert('Select customers first');
            return;
        }

        try {
            setBatchLoading(true);
            await api.batchInitiateCalls(selectedCustomers);
            alert(`Initiated calls to ${selectedCustomers.length} customers`);
            setSelectedCustomers([]);
            setShowBatchModal(false);
            loadData();
        } catch (err) {
            alert('Failed to initiate batch calls: ' + err.message);
        } finally {
            setBatchLoading(false);
        }
    }

    function toggleCustomerSelection(customerId) {
        setSelectedCustomers(prev =>
            prev.includes(customerId)
                ? prev.filter(id => id !== customerId)
                : [...prev, customerId]
        );
    }

    function formatDuration(seconds) {
        if (!seconds) return '-';
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }

    const filteredCalls = calls.filter(c =>
        c.customer_name?.toLowerCase().includes(search.toLowerCase()) ||
        c.customer_phone?.includes(search)
    );

    if (loading) {
        return <div className="loading"><div className="spinner"></div></div>;
    }

    return (
        <div>
            <div className="page-header">
                <h1>Calls</h1>
                <p>View call history and initiate new AI calls</p>
            </div>

            {error && (
                <div className="card" style={{ marginBottom: '1rem', background: 'rgba(239, 68, 68, 0.1)' }}>
                    <p style={{ color: 'var(--error)' }}>⚠️ {error}</p>
                </div>
            )}

            <div className="toolbar">
                <div className="search-input">
                    <span className="search-icon">🔍</span>
                    <input
                        type="text"
                        placeholder="Search calls..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                    />
                </div>
                <select
                    className="form-input form-select"
                    style={{ width: 'auto' }}
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                >
                    <option value="">All Statuses</option>
                    <option value="completed">Completed</option>
                    <option value="in_progress">In Progress</option>
                    <option value="initiated">Initiated</option>
                    <option value="failed">Failed</option>
                </select>
                <button className="btn btn-primary" onClick={() => setShowBatchModal(true)}>
                    📞 Batch Call
                </button>
            </div>

            {/* Call History */}
            <div className="data-table-container">
                <div className="data-table-header">
                    <h2>📞 Call History</h2>
                    <span className="badge badge-info">{filteredCalls.length} calls</span>
                </div>
                <table className="data-table">
                    <thead>
                        <tr>
                            <th>Customer</th>
                            <th>Status</th>
                            <th>Duration</th>
                            <th>Outcome</th>
                            <th>Date</th>
                            <th>Notes</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filteredCalls.length === 0 ? (
                            <tr>
                                <td colSpan="6">
                                    <div className="empty-state">
                                        <div className="icon">📞</div>
                                        <h3>No calls found</h3>
                                        <p>Initiate your first AI call to see history</p>
                                    </div>
                                </td>
                            </tr>
                        ) : (
                            filteredCalls.map((call) => (
                                <tr key={call.id}>
                                    <td>
                                        <div className="flex items-center gap-md">
                                            <div className="avatar">{call.customer_name?.[0] || '?'}</div>
                                            <div>
                                                <div className="font-medium">{call.customer_name || 'Unknown'}</div>
                                                <div className="text-muted text-sm">{call.customer_phone}</div>
                                            </div>
                                        </div>
                                    </td>
                                    <td>
                                        <StatusBadge status={call.status} />
                                    </td>
                                    <td>
                                        <span className="font-medium">{formatDuration(call.duration_seconds)}</span>
                                    </td>
                                    <td>
                                        {call.outcome ? (
                                            <StatusBadge status={call.outcome} />
                                        ) : (
                                            <span className="text-muted">-</span>
                                        )}
                                    </td>
                                    <td>
                                        <div className="text-sm">
                                            {call.started_at ? new Date(call.started_at).toLocaleString() : '-'}
                                        </div>
                                    </td>
                                    <td>
                                        <div className="text-sm text-muted" style={{ maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                            {call.notes || '-'}
                                        </div>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>

            {/* Batch Call Modal */}
            {showBatchModal && (
                <div className="modal-overlay" onClick={() => setShowBatchModal(false)}>
                    <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: '600px' }}>
                        <div className="modal-header">
                            <h2>📞 Batch Call</h2>
                            <button className="modal-close" onClick={() => setShowBatchModal(false)}>✕</button>
                        </div>
                        <div className="modal-body">
                            <p className="text-muted" style={{ marginBottom: '1rem' }}>
                                Select customers to call ({selectedCustomers.length} selected)
                            </p>
                            <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
                                {customers.map(customer => (
                                    <div
                                        key={customer.id}
                                        className="list-item"
                                        style={{ cursor: 'pointer', background: selectedCustomers.includes(customer.id) ? 'var(--bg-glass)' : 'transparent' }}
                                        onClick={() => toggleCustomerSelection(customer.id)}
                                    >
                                        <input
                                            type="checkbox"
                                            checked={selectedCustomers.includes(customer.id)}
                                            onChange={() => { }}
                                            style={{ accentColor: 'var(--accent-primary)' }}
                                        />
                                        <div className="avatar">{customer.name?.[0] || '?'}</div>
                                        <div className="item-content">
                                            <div className="item-title">{customer.name}</div>
                                            <div className="item-subtitle">{customer.phone}</div>
                                        </div>
                                        {customer.last_call_date && (
                                            <div className="text-muted text-sm">
                                                Last called: {new Date(customer.last_call_date).toLocaleDateString()}
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>
                        <div className="modal-footer">
                            <button className="btn btn-secondary" onClick={() => setShowBatchModal(false)}>
                                Cancel
                            </button>
                            <button
                                className="btn btn-primary"
                                onClick={handleBatchCall}
                                disabled={batchLoading || selectedCustomers.length === 0}
                            >
                                {batchLoading ? 'Calling...' : `Call ${selectedCustomers.length} Customers`}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

export default Calls;
