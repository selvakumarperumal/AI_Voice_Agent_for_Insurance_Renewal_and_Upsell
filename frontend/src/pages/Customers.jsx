import { useState, useEffect } from 'react';
import api from '../api/client';
import Modal from '../components/Modal';
import StatusBadge from '../components/StatusBadge';

function Customers() {
    const [customers, setCustomers] = useState([]);
    const [policies, setPolicies] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [search, setSearch] = useState('');
    const [showModal, setShowModal] = useState(false);
    const [showPoliciesModal, setShowPoliciesModal] = useState(false);
    const [showAttachModal, setShowAttachModal] = useState(false);
    const [selectedCustomer, setSelectedCustomer] = useState(null);
    const [customerPolicies, setCustomerPolicies] = useState([]);
    const [editingCustomer, setEditingCustomer] = useState(null);
    const [formData, setFormData] = useState({
        name: '',
        phone: '',
        email: '',
        age: '',
        city: '',
        address: ''
    });
    const [attachFormData, setAttachFormData] = useState({
        policy_id: '',
        start_date: '',
        end_date: '',
        premium_amount: '',
        sum_assured: ''
    });
    const [calling, setCalling] = useState(null);
    const [loadingPolicies, setLoadingPolicies] = useState(false);
    const [attaching, setAttaching] = useState(false);
    const [showDeleteModal, setShowDeleteModal] = useState(false);
    const [customerToDelete, setCustomerToDelete] = useState(null);
    const [deleting, setDeleting] = useState(false);

    useEffect(() => {
        loadData();
    }, []);

    async function loadData() {
        try {
            setLoading(true);
            const [customersData, policiesData] = await Promise.all([
                api.getCustomers(),
                api.getPolicies()
            ]);
            setCustomers(Array.isArray(customersData) ? customersData : []);
            setPolicies(Array.isArray(policiesData) ? policiesData : []);
        } catch (err) {
            setError('Failed to load data');
            console.error(err);
        } finally {
            setLoading(false);
        }
    }

    function openAddModal() {
        setEditingCustomer(null);
        setFormData({ name: '', phone: '', email: '', age: '', city: '', address: '' });
        setShowModal(true);
    }

    function openEditModal(customer) {
        setEditingCustomer(customer);
        setFormData({
            name: customer.name || '',
            phone: customer.phone || '',
            email: customer.email || '',
            age: customer.age || '',
            city: customer.city || '',
            address: customer.address || ''
        });
        setShowModal(true);
    }

    async function openPoliciesModal(customer) {
        setSelectedCustomer(customer);
        setLoadingPolicies(true);
        setShowPoliciesModal(true);

        try {
            const pols = await api.getCustomerPolicies(customer.id);
            setCustomerPolicies(Array.isArray(pols) ? pols : []);
        } catch (err) {
            console.error('Failed to load policies:', err);
            setCustomerPolicies([]);
        } finally {
            setLoadingPolicies(false);
        }
    }

    function openAttachModal(customer) {
        setSelectedCustomer(customer);
        const today = new Date().toISOString().split('T')[0];
        setAttachFormData({
            policy_id: '',
            start_date: today,
            end_date: '',
            premium_amount: '',
            sum_assured: '',
            duration_months: 12
        });
        setShowAttachModal(true);
    }

    function calculateEndDate(startDate, durationMonths) {
        if (!startDate || !durationMonths) return '';
        const start = new Date(startDate);
        start.setMonth(start.getMonth() + durationMonths);
        return start.toISOString().split('T')[0];
    }

    function handlePolicySelect(policyId) {
        const policy = policies.find(p => p.id === policyId);
        if (!policy) {
            setAttachFormData({ ...attachFormData, policy_id: '' });
            return;
        }
        const endDate = calculateEndDate(attachFormData.start_date, policy.duration_months);
        setAttachFormData({
            ...attachFormData,
            policy_id: policyId,
            end_date: endDate,
            premium_amount: policy.base_premium || '',
            sum_assured: policy.base_sum_assured || '',
            duration_months: policy.duration_months || 12
        });
    }

    function handleStartDateChange(startDate) {
        const endDate = calculateEndDate(startDate, attachFormData.duration_months);
        setAttachFormData({
            ...attachFormData,
            start_date: startDate,
            end_date: endDate
        });
    }

    async function handleSubmit(e) {
        e.preventDefault();
        try {
            const payload = {
                ...formData,
                age: formData.age ? parseInt(formData.age) : null
            };

            if (editingCustomer) {
                await api.updateCustomer(editingCustomer.id, payload);
            } else {
                await api.createCustomer(payload);
            }

            setShowModal(false);
            loadData();
        } catch (err) {
            alert('Failed to save customer: ' + err.message);
        }
    }

    async function handleAttachPolicy(e) {
        e.preventDefault();
        if (!attachFormData.policy_id) {
            alert('Please select a policy');
            return;
        }

        try {
            setAttaching(true);
            await api.attachPolicyToCustomer(selectedCustomer.id, {
                policy_id: attachFormData.policy_id,
                start_date: attachFormData.start_date,
                end_date: attachFormData.end_date,
                premium_amount: parseInt(attachFormData.premium_amount) || undefined,
                sum_assured: parseInt(attachFormData.sum_assured) || undefined
            });
            setShowAttachModal(false);
            alert(`Policy attached to ${selectedCustomer.name}`);
        } catch (err) {
            alert('Failed to attach policy: ' + err.message);
        } finally {
            setAttaching(false);
        }
    }

    async function handleDetachPolicy(customerId, customerPolicyId) {
        console.log('Detaching policy:', customerId, customerPolicyId);
        try {
            await api.detachPolicyFromCustomer(customerId, customerPolicyId);
            console.log('Detach successful, refreshing list...');
            const pols = await api.getCustomerPolicies(customerId);
            console.log('Got policies:', pols);
            setCustomerPolicies(Array.isArray(pols) ? pols : []);
        } catch (err) {
            console.error('Detach error:', err);
            alert('Failed to detach policy: ' + err.message);
        }
    }

    function openDeleteModal(customer) {
        setCustomerToDelete(customer);
        setShowDeleteModal(true);
    }

    async function handleConfirmDelete() {
        if (!customerToDelete) return;
        try {
            setDeleting(true);
            await api.deleteCustomer(customerToDelete.id);
            setShowDeleteModal(false);
            setCustomerToDelete(null);
            loadData();
        } catch (err) {
            alert('Failed to delete customer: ' + err.message);
        } finally {
            setDeleting(false);
        }
    }

    async function handleInitiateCall(customer) {
        try {
            setCalling(customer.id);
            await api.initiateCall(customer.id);
            alert(`Call initiated to ${customer.name}`);
            loadData();
        } catch (err) {
            alert('Failed to initiate call: ' + err.message);
        } finally {
            setCalling(null);
        }
    }

    const filteredCustomers = customers.filter(c =>
        c.name?.toLowerCase().includes(search.toLowerCase()) ||
        c.phone?.includes(search) ||
        c.email?.toLowerCase().includes(search.toLowerCase()) ||
        c.city?.toLowerCase().includes(search.toLowerCase())
    );

    if (loading) {
        return <div className="loading"><div className="spinner"></div></div>;
    }

    return (
        <div>
            <div className="page-header">
                <h1>Customers</h1>
                <p>Manage customers and attach policies</p>
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
                        placeholder="Search customers..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                    />
                </div>
                <button className="btn btn-primary" onClick={openAddModal}>
                    ➕ Add Customer
                </button>
            </div>

            <div className="data-table-container">
                <table className="data-table">
                    <thead>
                        <tr>
                            <th>Customer</th>
                            <th>Contact</th>
                            <th>Location</th>
                            <th>Last Call</th>
                            <th>Status</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filteredCustomers.length === 0 ? (
                            <tr>
                                <td colSpan="6">
                                    <div className="empty-state">
                                        <div className="icon">👥</div>
                                        <h3>No customers found</h3>
                                        <p>Add your first customer to get started</p>
                                    </div>
                                </td>
                            </tr>
                        ) : (
                            filteredCustomers.map((customer) => (
                                <tr key={customer.id}>
                                    <td>
                                        <div className="flex items-center gap-md">
                                            <div className="avatar">{customer.name?.[0] || '?'}</div>
                                            <div>
                                                <div className="font-medium">{customer.name}</div>
                                                <div className="text-muted text-sm">{customer.customer_code || '-'}</div>
                                            </div>
                                        </div>
                                    </td>
                                    <td>
                                        <div>{customer.phone}</div>
                                        <div className="text-muted text-sm">{customer.email || '-'}</div>
                                    </td>
                                    <td>
                                        <div>{customer.city || '-'}</div>
                                        {customer.age && <div className="text-muted text-sm">Age: {customer.age}</div>}
                                    </td>
                                    <td>
                                        {customer.last_call_date ? (
                                            <div className="text-sm">
                                                {new Date(customer.last_call_date).toLocaleDateString()}
                                            </div>
                                        ) : (
                                            <span className="text-muted">Never</span>
                                        )}
                                    </td>
                                    <td>
                                        {customer.call_status ? (
                                            <StatusBadge status={customer.call_status} />
                                        ) : (
                                            <span className="text-muted">-</span>
                                        )}
                                    </td>
                                    <td>
                                        <div className="quick-actions">
                                            <button
                                                className="btn btn-primary btn-sm"
                                                onClick={() => openAttachModal(customer)}
                                                title="Attach Policy"
                                            >
                                                📎
                                            </button>
                                            <button
                                                className="btn btn-secondary btn-sm"
                                                onClick={() => openPoliciesModal(customer)}
                                                title="View Policies"
                                            >
                                                📋
                                            </button>
                                            <button
                                                className="btn btn-success btn-sm"
                                                onClick={() => handleInitiateCall(customer)}
                                                disabled={calling === customer.id}
                                                title="Call"
                                            >
                                                {calling === customer.id ? '...' : '📞'}
                                            </button>
                                            <button
                                                className="btn btn-secondary btn-sm"
                                                onClick={() => openEditModal(customer)}
                                                title="Edit"
                                            >
                                                ✏️
                                            </button>
                                            <button
                                                className="btn btn-danger btn-sm"
                                                onClick={() => openDeleteModal(customer)}
                                                title="Delete"
                                            >
                                                🗑️
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>

            {/* Add/Edit Customer Modal */}
            <Modal
                isOpen={showModal}
                onClose={() => setShowModal(false)}
                title={editingCustomer ? 'Edit Customer' : 'Add Customer'}
                footer={
                    <>
                        <button className="btn btn-secondary" onClick={() => setShowModal(false)}>
                            Cancel
                        </button>
                        <button className="btn btn-primary" onClick={handleSubmit}>
                            {editingCustomer ? 'Update' : 'Create'}
                        </button>
                    </>
                }
            >
                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label className="form-label">Name *</label>
                        <input
                            className="form-input"
                            type="text"
                            value={formData.name}
                            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                            required
                        />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Phone * (E.164 format: +919123456789)</label>
                        <input
                            className="form-input"
                            type="tel"
                            value={formData.phone}
                            onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                            placeholder="+919123456789"
                            required
                        />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Email</label>
                        <input
                            className="form-input"
                            type="email"
                            value={formData.email}
                            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                        />
                    </div>
                    <div className="grid-2">
                        <div className="form-group">
                            <label className="form-label">Age</label>
                            <input
                                className="form-input"
                                type="number"
                                value={formData.age}
                                onChange={(e) => setFormData({ ...formData, age: e.target.value })}
                            />
                        </div>
                        <div className="form-group">
                            <label className="form-label">City</label>
                            <input
                                className="form-input"
                                type="text"
                                value={formData.city}
                                onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                            />
                        </div>
                    </div>
                    <div className="form-group">
                        <label className="form-label">Address</label>
                        <input
                            className="form-input"
                            type="text"
                            value={formData.address}
                            onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                        />
                    </div>
                </form>
            </Modal>

            {/* View Policies Modal */}
            <Modal
                isOpen={showPoliciesModal}
                onClose={() => setShowPoliciesModal(false)}
                title={`Policies - ${selectedCustomer?.name || ''}`}
                footer={
                    <>
                        <button className="btn btn-primary" onClick={() => { setShowPoliciesModal(false); openAttachModal(selectedCustomer); }}>
                            📎 Attach Policy
                        </button>
                        <button className="btn btn-secondary" onClick={() => setShowPoliciesModal(false)}>
                            Close
                        </button>
                    </>
                }
            >
                {loadingPolicies ? (
                    <div className="loading"><div className="spinner"></div></div>
                ) : customerPolicies.length === 0 ? (
                    <div className="empty-state">
                        <div className="icon">📋</div>
                        <h3>No policies attached</h3>
                        <p>Click "Attach Policy" to add a policy to this customer.</p>
                    </div>
                ) : (
                    <div>
                        {customerPolicies.map(cp => (
                            <div key={cp.id} className="list-item" style={{ marginBottom: '0.5rem', padding: '1rem', background: 'var(--bg-glass)', borderRadius: 'var(--radius-lg)', display: 'flex', alignItems: 'center', gap: '1rem' }}>
                                <div className="item-icon">📋</div>
                                <div style={{ flex: 1 }}>
                                    <div className="font-medium">{cp.policy_name || cp.policy_number}</div>
                                    <div className="text-muted text-sm">
                                        {cp.product_name} • ₹{cp.premium_amount?.toLocaleString()}/yr
                                    </div>
                                    <div className="text-muted text-sm">
                                        {new Date(cp.start_date).toLocaleDateString()} - {new Date(cp.end_date).toLocaleDateString()}
                                        {cp.days_to_expiry !== null && cp.days_to_expiry <= 30 && (
                                            <span className="badge badge-warning" style={{ marginLeft: '0.5rem' }}>
                                                {cp.days_to_expiry} days left
                                            </span>
                                        )}
                                    </div>
                                </div>
                                <StatusBadge status={cp.status} />
                                {cp.status === 'active' && (
                                    <button
                                        className="btn btn-danger btn-sm"
                                        onClick={() => handleDetachPolicy(selectedCustomer.id, cp.id)}
                                        title="Cancel"
                                    >
                                        ✕
                                    </button>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </Modal>

            {/* Attach Policy Modal */}
            <Modal
                isOpen={showAttachModal}
                onClose={() => setShowAttachModal(false)}
                title={`Attach Policy to ${selectedCustomer?.name || ''}`}
                footer={
                    <>
                        <button className="btn btn-secondary" onClick={() => setShowAttachModal(false)}>
                            Cancel
                        </button>
                        <button className="btn btn-primary" onClick={handleAttachPolicy} disabled={attaching}>
                            {attaching ? 'Attaching...' : 'Attach Policy'}
                        </button>
                    </>
                }
            >
                <form onSubmit={handleAttachPolicy}>
                    <div className="form-group">
                        <label className="form-label">Policy Template *</label>
                        <select
                            className="form-input form-select"
                            value={attachFormData.policy_id}
                            onChange={(e) => handlePolicySelect(e.target.value)}
                            required
                        >
                            <option value="">Select a policy template...</option>
                            {policies.filter(p => p.is_active).map(policy => (
                                <option key={policy.id} value={policy.id}>
                                    {policy.policy_name || policy.policy_number} - {policy.duration_months} months - ₹{policy.base_premium?.toLocaleString()}/yr
                                </option>
                            ))}
                        </select>
                    </div>

                    {attachFormData.policy_id && (
                        <div style={{ padding: '1rem', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', marginBottom: '1rem' }}>
                            <div className="grid-2">
                                <div>
                                    <div className="text-muted text-sm">Premium</div>
                                    <div className="font-medium">₹{parseInt(attachFormData.premium_amount)?.toLocaleString()}/yr</div>
                                </div>
                                <div>
                                    <div className="text-muted text-sm">Sum Assured</div>
                                    <div className="font-medium">₹{(parseInt(attachFormData.sum_assured) / 100000).toFixed(1)}L</div>
                                </div>
                            </div>
                            <div style={{ marginTop: '0.5rem' }}>
                                <div className="text-muted text-sm">Duration</div>
                                <div className="font-medium">{attachFormData.duration_months} months</div>
                            </div>
                        </div>
                    )}

                    <div className="grid-2">
                        <div className="form-group">
                            <label className="form-label">Start Date *</label>
                            <input
                                className="form-input"
                                type="date"
                                value={attachFormData.start_date}
                                onChange={(e) => handleStartDateChange(e.target.value)}
                                required
                            />
                        </div>
                        <div className="form-group">
                            <label className="form-label">End Date (auto-calculated)</label>
                            <input
                                className="form-input"
                                type="date"
                                value={attachFormData.end_date}
                                readOnly
                                style={{ opacity: 0.7, cursor: 'not-allowed' }}
                            />
                        </div>
                    </div>
                </form>
            </Modal>

            {/* Delete Confirmation Modal */}
            <Modal
                isOpen={showDeleteModal}
                onClose={() => setShowDeleteModal(false)}
                title="Delete Customer"
                footer={
                    <>
                        <button className="btn btn-secondary" onClick={() => setShowDeleteModal(false)}>
                            Cancel
                        </button>
                        <button className="btn btn-danger" onClick={handleConfirmDelete} disabled={deleting}>
                            {deleting ? 'Deleting...' : 'Delete'}
                        </button>
                    </>
                }
            >
                <p>Are you sure you want to delete <strong>{customerToDelete?.name}</strong>?</p>
                <p className="text-muted text-sm">This action cannot be undone. All associated data will be removed.</p>
            </Modal>
        </div>
    );
}

export default Customers;
