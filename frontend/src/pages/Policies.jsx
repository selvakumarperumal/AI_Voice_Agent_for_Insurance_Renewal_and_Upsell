import { useState, useEffect } from 'react';
import api from '../api/client';
import Modal from '../components/Modal';
import StatusBadge from '../components/StatusBadge';

function Policies() {
    const [policies, setPolicies] = useState([]);
    const [products, setProducts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [search, setSearch] = useState('');
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [creating, setCreating] = useState(false);
    const [formData, setFormData] = useState({
        policy_number: '',
        policy_name: '',
        product_id: '',
        base_premium: '',
        base_sum_assured: '',
        duration_months: '12',
        description: ''
    });

    useEffect(() => {
        loadData();
    }, []);

    async function loadData() {
        try {
            setLoading(true);
            const [policiesData, productsData] = await Promise.all([
                api.getPolicies(),
                api.getProducts()
            ]);
            setPolicies(Array.isArray(policiesData) ? policiesData : []);
            setProducts(Array.isArray(productsData) ? productsData : []);
        } catch (err) {
            setError('Failed to load data');
            console.error(err);
        } finally {
            setLoading(false);
        }
    }

    function openCreateModal() {
        setFormData({
            policy_number: `POL-${Date.now().toString().slice(-6)}`,
            policy_name: '',
            product_id: '',
            base_premium: '',
            base_sum_assured: '',
            duration_months: '12',
            description: ''
        });
        setShowCreateModal(true);
    }

    async function handleCreatePolicy(e) {
        e.preventDefault();

        if (!formData.product_id) {
            alert('Please select a product');
            return;
        }

        try {
            setCreating(true);
            await api.createPolicy({
                ...formData,
                base_premium: parseInt(formData.base_premium) || 0,
                base_sum_assured: parseInt(formData.base_sum_assured) || 0,
                duration_months: parseInt(formData.duration_months) || 12
            });
            setShowCreateModal(false);
            loadData();
        } catch (err) {
            alert('Failed to create policy: ' + err.message);
        } finally {
            setCreating(false);
        }
    }

    async function handleToggleActive(policy) {
        try {
            await api.updatePolicy(policy.id, { is_active: !policy.is_active });
            loadData();
        } catch (err) {
            alert('Failed to update policy');
        }
    }

    function getProductName(productId) {
        const product = products.find(p => p.id === productId);
        return product?.product_name || 'Unknown';
    }

    function getProductType(productId) {
        const product = products.find(p => p.id === productId);
        return product?.product_type || '';
    }

    const filteredPolicies = policies.filter(p =>
        p.policy_number?.toLowerCase().includes(search.toLowerCase()) ||
        p.policy_name?.toLowerCase().includes(search.toLowerCase()) ||
        getProductName(p.product_id).toLowerCase().includes(search.toLowerCase())
    );

    if (loading) {
        return <div className="loading"><div className="spinner"></div></div>;
    }

    return (
        <div>
            <div className="page-header">
                <h1>Policy Templates</h1>
                <p>Create and manage policy templates. Attach to customers from Customers page.</p>
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
                        placeholder="Search policies..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                    />
                </div>
                <button className="btn btn-primary" onClick={openCreateModal}>
                    ➕ Create Policy Template
                </button>
            </div>

            <div className="data-table-container">
                <div className="data-table-header">
                    <h2>📋 Policy Templates</h2>
                    <span className="badge badge-info">{filteredPolicies.length} templates</span>
                </div>
                <table className="data-table">
                    <thead>
                        <tr>
                            <th>Policy</th>
                            <th>Product</th>
                            <th>Base Premium</th>
                            <th>Coverage</th>
                            <th>Duration</th>
                            <th>Status</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filteredPolicies.length === 0 ? (
                            <tr>
                                <td colSpan="7">
                                    <div className="empty-state">
                                        <div className="icon">📋</div>
                                        <h3>No policy templates</h3>
                                        <p>Create your first policy template</p>
                                    </div>
                                </td>
                            </tr>
                        ) : (
                            filteredPolicies.map((policy) => (
                                <tr key={policy.id}>
                                    <td>
                                        <div className="font-medium">{policy.policy_name || policy.policy_number}</div>
                                        <div className="text-muted text-sm">{policy.policy_number}</div>
                                    </td>
                                    <td>
                                        <div>{getProductName(policy.product_id)}</div>
                                        <div className="text-muted text-sm">{getProductType(policy.product_id)}</div>
                                    </td>
                                    <td>
                                        <div className="font-medium">₹{policy.base_premium?.toLocaleString()}/yr</div>
                                    </td>
                                    <td>
                                        <div className="font-medium">₹{(policy.base_sum_assured / 100000).toFixed(0)}L</div>
                                    </td>
                                    <td>
                                        <div>{policy.duration_months} months</div>
                                    </td>
                                    <td>
                                        <StatusBadge status={policy.is_active ? 'active' : 'inactive'} />
                                    </td>
                                    <td>
                                        <div className="quick-actions">
                                            <button
                                                className={`btn btn-sm ${policy.is_active ? 'btn-danger' : 'btn-success'}`}
                                                onClick={() => handleToggleActive(policy)}
                                                title={policy.is_active ? 'Deactivate' : 'Activate'}
                                            >
                                                {policy.is_active ? '⏸️' : '▶️'}
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>

            {/* Create Policy Template Modal */}
            <Modal
                isOpen={showCreateModal}
                onClose={() => setShowCreateModal(false)}
                title="Create Policy Template"
                footer={
                    <>
                        <button className="btn btn-secondary" onClick={() => setShowCreateModal(false)}>
                            Cancel
                        </button>
                        <button className="btn btn-primary" onClick={handleCreatePolicy} disabled={creating}>
                            {creating ? 'Creating...' : 'Create Template'}
                        </button>
                    </>
                }
            >
                <form onSubmit={handleCreatePolicy}>
                    <div className="grid-2">
                        <div className="form-group">
                            <label className="form-label">Policy Number *</label>
                            <input
                                className="form-input"
                                type="text"
                                value={formData.policy_number}
                                onChange={(e) => setFormData({ ...formData, policy_number: e.target.value })}
                                required
                            />
                        </div>
                        <div className="form-group">
                            <label className="form-label">Policy Name *</label>
                            <input
                                className="form-input"
                                type="text"
                                placeholder="e.g., Family Health Basic 2024"
                                value={formData.policy_name}
                                onChange={(e) => setFormData({ ...formData, policy_name: e.target.value })}
                                required
                            />
                        </div>
                    </div>

                    <div className="form-group">
                        <label className="form-label">Product *</label>
                        <select
                            className="form-input form-select"
                            value={formData.product_id}
                            onChange={(e) => {
                                const product = products.find(p => p.id === e.target.value);
                                setFormData({
                                    ...formData,
                                    product_id: e.target.value,
                                    base_premium: product?.base_premium || '',
                                    base_sum_assured: product?.sum_assured_options?.[0] || ''
                                });
                            }}
                            required
                        >
                            <option value="">Select a product...</option>
                            {products.filter(p => p.is_active).map(product => (
                                <option key={product.id} value={product.id}>
                                    {product.product_name} ({product.product_type}) - Base ₹{product.base_premium}
                                </option>
                            ))}
                        </select>
                    </div>

                    <div className="grid-2">
                        <div className="form-group">
                            <label className="form-label">Base Premium (₹/year) *</label>
                            <input
                                className="form-input"
                                type="number"
                                value={formData.base_premium}
                                onChange={(e) => setFormData({ ...formData, base_premium: e.target.value })}
                                required
                            />
                        </div>
                        <div className="form-group">
                            <label className="form-label">Base Sum Assured (₹) *</label>
                            <input
                                className="form-input"
                                type="number"
                                value={formData.base_sum_assured}
                                onChange={(e) => setFormData({ ...formData, base_sum_assured: e.target.value })}
                                required
                            />
                        </div>
                    </div>

                    <div className="form-group">
                        <label className="form-label">Duration (months)</label>
                        <select
                            className="form-input form-select"
                            value={formData.duration_months}
                            onChange={(e) => setFormData({ ...formData, duration_months: e.target.value })}
                        >
                            <option value="6">6 months</option>
                            <option value="12">12 months (1 year)</option>
                            <option value="24">24 months (2 years)</option>
                            <option value="36">36 months (3 years)</option>
                        </select>
                    </div>

                    <div className="form-group">
                        <label className="form-label">Description</label>
                        <input
                            className="form-input"
                            type="text"
                            placeholder="Optional description"
                            value={formData.description}
                            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                        />
                    </div>
                </form>
            </Modal>
        </div>
    );
}

export default Policies;
