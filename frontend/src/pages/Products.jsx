import { useState, useEffect } from 'react';
import api from '../api/client';
import Modal from '../components/Modal';
import StatusBadge from '../components/StatusBadge';

function Products() {
    const [products, setProducts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [search, setSearch] = useState('');
    const [typeFilter, setTypeFilter] = useState('');
    const [showModal, setShowModal] = useState(false);
    const [editingProduct, setEditingProduct] = useState(null);
    const [formData, setFormData] = useState({
        product_code: '',
        product_name: '',
        product_type: 'Health',
        base_premium: '',
        description: '',
        features: '',
        sum_assured_options: '',
        min_age: '18',
        max_age: '65'
    });

    useEffect(() => {
        loadProducts();
    }, [typeFilter]);

    async function loadProducts() {
        try {
            setLoading(true);
            const params = {};
            if (typeFilter) params.product_type = typeFilter;
            const data = await api.getProducts(params);
            setProducts(Array.isArray(data) ? data : []);
        } catch (err) {
            setError('Failed to load products');
            console.error(err);
        } finally {
            setLoading(false);
        }
    }

    function openAddModal() {
        setEditingProduct(null);
        setFormData({
            product_code: '',
            product_name: '',
            product_type: 'Health',
            base_premium: '',
            description: '',
            features: '',
            sum_assured_options: '',
            min_age: '18',
            max_age: '65'
        });
        setShowModal(true);
    }

    function openEditModal(product) {
        setEditingProduct(product);
        setFormData({
            product_code: product.product_code || '',
            product_name: product.product_name || '',
            product_type: product.product_type || 'Health',
            base_premium: product.base_premium || '',
            description: product.description || '',
            features: (product.features || []).join(', '),
            sum_assured_options: (product.sum_assured_options || []).join(', '),
            min_age: product.min_age?.toString() || '18',
            max_age: product.max_age?.toString() || '65'
        });
        setShowModal(true);
    }

    async function handleSubmit(e) {
        e.preventDefault();
        try {
            const payload = {
                ...formData,
                base_premium: parseInt(formData.base_premium) || 0,
                features: formData.features.split(',').map(f => f.trim()).filter(Boolean),
                sum_assured_options: formData.sum_assured_options.split(',').map(s => parseInt(s.trim())).filter(Boolean),
                min_age: parseInt(formData.min_age) || 18,
                max_age: parseInt(formData.max_age) || 65,
                eligibility: {}
            };

            if (editingProduct) {
                await api.updateProduct(editingProduct.id, payload);
            } else {
                await api.createProduct(payload);
            }

            setShowModal(false);
            loadProducts();
        } catch (err) {
            alert('Failed to save product: ' + err.message);
        }
    }

    async function handleToggleActive(product) {
        try {
            await api.updateProduct(product.id, { is_active: !product.is_active });
            loadProducts();
        } catch (err) {
            alert('Failed to update product');
        }
    }

    const filteredProducts = products.filter(p =>
        p.product_name?.toLowerCase().includes(search.toLowerCase()) ||
        p.product_code?.toLowerCase().includes(search.toLowerCase())
    );

    if (loading) {
        return <div className="loading"><div className="spinner"></div></div>;
    }

    return (
        <div>
            <div className="page-header">
                <h1>Products</h1>
                <p>Insurance product catalog</p>
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
                        placeholder="Search products..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                    />
                </div>
                <select
                    className="form-input form-select"
                    style={{ width: 'auto' }}
                    value={typeFilter}
                    onChange={(e) => setTypeFilter(e.target.value)}
                >
                    <option value="">All Types</option>
                    <option value="Health">Health</option>
                    <option value="Life">Life</option>
                    <option value="Motor">Motor</option>
                    <option value="Home">Home</option>
                </select>
                <button className="btn btn-primary" onClick={openAddModal}>
                    ➕ Add Product
                </button>
            </div>

            <div className="data-table-container">
                <table className="data-table">
                    <thead>
                        <tr>
                            <th>Product</th>
                            <th>Type</th>
                            <th>Base Premium</th>
                            <th>Age Range</th>
                            <th>Sum Assured</th>
                            <th>Status</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filteredProducts.length === 0 ? (
                            <tr>
                                <td colSpan="7">
                                    <div className="empty-state">
                                        <div className="icon">📦</div>
                                        <h3>No products found</h3>
                                        <p>Add your first insurance product</p>
                                    </div>
                                </td>
                            </tr>
                        ) : (
                            filteredProducts.map((product) => (
                                <tr key={product.id}>
                                    <td>
                                        <div className="font-medium">{product.product_name}</div>
                                        <div className="text-muted text-sm">{product.product_code}</div>
                                    </td>
                                    <td>
                                        <StatusBadge status={product.product_type} />
                                    </td>
                                    <td>
                                        <div className="font-medium">₹{product.base_premium?.toLocaleString()}</div>
                                    </td>
                                    <td>
                                        <div className="text-sm">{product.min_age || 18} - {product.max_age || 65} yrs</div>
                                    </td>
                                    <td>
                                        <div className="text-sm">
                                            {product.sum_assured_options?.slice(0, 3).map(s => `₹${(s / 100000).toFixed(0)}L`).join(', ') || '-'}
                                        </div>
                                    </td>
                                    <td>
                                        <StatusBadge status={product.is_active?.toString()} />
                                    </td>
                                    <td>
                                        <div className="quick-actions">
                                            <button
                                                className="btn btn-secondary btn-sm"
                                                onClick={() => openEditModal(product)}
                                            >
                                                ✏️
                                            </button>
                                            <button
                                                className={`btn btn-sm ${product.is_active ? 'btn-danger' : 'btn-success'}`}
                                                onClick={() => handleToggleActive(product)}
                                            >
                                                {product.is_active ? '⏸️' : '▶️'}
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>

            {/* Add/Edit Modal */}
            <Modal
                isOpen={showModal}
                onClose={() => setShowModal(false)}
                title={editingProduct ? 'Edit Product' : 'Add Product'}
                footer={
                    <>
                        <button className="btn btn-secondary" onClick={() => setShowModal(false)}>Cancel</button>
                        <button className="btn btn-primary" onClick={handleSubmit}>
                            {editingProduct ? 'Update' : 'Create'}
                        </button>
                    </>
                }
            >
                <form onSubmit={handleSubmit}>
                    <div className="grid-2">
                        <div className="form-group">
                            <label className="form-label">Product Code *</label>
                            <input
                                className="form-input"
                                type="text"
                                value={formData.product_code}
                                onChange={(e) => setFormData({ ...formData, product_code: e.target.value })}
                                required
                                disabled={!!editingProduct}
                            />
                        </div>
                        <div className="form-group">
                            <label className="form-label">Type *</label>
                            <select
                                className="form-input form-select"
                                value={formData.product_type}
                                onChange={(e) => setFormData({ ...formData, product_type: e.target.value })}
                            >
                                <option value="Health">Health</option>
                                <option value="Life">Life</option>
                                <option value="Motor">Motor</option>
                                <option value="Home">Home</option>
                            </select>
                        </div>
                    </div>
                    <div className="form-group">
                        <label className="form-label">Product Name *</label>
                        <input
                            className="form-input"
                            type="text"
                            value={formData.product_name}
                            onChange={(e) => setFormData({ ...formData, product_name: e.target.value })}
                            required
                        />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Base Premium (₹) *</label>
                        <input
                            className="form-input"
                            type="number"
                            value={formData.base_premium}
                            onChange={(e) => setFormData({ ...formData, base_premium: e.target.value })}
                            required
                        />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Sum Assured Options (comma-separated)</label>
                        <input
                            className="form-input"
                            type="text"
                            value={formData.sum_assured_options}
                            placeholder="500000, 1000000, 2000000"
                            onChange={(e) => setFormData({ ...formData, sum_assured_options: e.target.value })}
                        />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Features (comma-separated)</label>
                        <input
                            className="form-input"
                            type="text"
                            value={formData.features}
                            placeholder="Cashless claim, No waiting period"
                            onChange={(e) => setFormData({ ...formData, features: e.target.value })}
                        />
                    </div>
                    <div className="grid-2">
                        <div className="form-group">
                            <label className="form-label">Min Age</label>
                            <input
                                className="form-input"
                                type="number"
                                value={formData.min_age}
                                onChange={(e) => setFormData({ ...formData, min_age: e.target.value })}
                                min="0"
                                max="100"
                            />
                        </div>
                        <div className="form-group">
                            <label className="form-label">Max Age</label>
                            <input
                                className="form-input"
                                type="number"
                                value={formData.max_age}
                                onChange={(e) => setFormData({ ...formData, max_age: e.target.value })}
                                min="0"
                                max="100"
                            />
                        </div>
                    </div>
                    <div className="form-group">
                        <label className="form-label">Description</label>
                        <input
                            className="form-input"
                            type="text"
                            value={formData.description}
                            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                        />
                    </div>
                </form>
            </Modal>
        </div>
    );
}

export default Products;
