// API Client for Insurance Backend
const API_BASE = 'http://localhost:8000/api';

class ApiClient {
    async fetch(endpoint, options = {}) {
        const url = `${API_BASE}${endpoint}`;
        const config = {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
        };

        try {
            const response = await fetch(url, config);
            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                throw new Error(error.detail || `HTTP ${response.status}`);
            }
            // Handle 204 No Content responses (DELETE operations)
            if (response.status === 204) {
                return true;
            }
            return response.json();
        } catch (error) {
            console.error(`API Error: ${endpoint}`, error);
            throw error;
        }
    }

    // Products
    async getProducts(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.fetch(`/products${query ? `?${query}` : ''}`);
    }

    async getProduct(id) {
        return this.fetch(`/products/${id}`);
    }

    async createProduct(data) {
        return this.fetch('/products', { method: 'POST', body: JSON.stringify(data) });
    }

    async updateProduct(id, data) {
        return this.fetch(`/products/${id}`, { method: 'PUT', body: JSON.stringify(data) });
    }

    async deleteProduct(id) {
        return this.fetch(`/products/${id}`, { method: 'DELETE' });
    }

    // Customers
    async getCustomers(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.fetch(`/customers${query ? `?${query}` : ''}`);
    }

    async getCustomer(id) {
        return this.fetch(`/customers/${id}`);
    }

    async getCustomerPolicies(customerId) {
        return this.fetch(`/customers/${customerId}/policies`);
    }

    async attachPolicyToCustomer(customerId, data) {
        return this.fetch(`/customers/${customerId}/policies`, { method: 'POST', body: JSON.stringify(data) });
    }

    async detachPolicyFromCustomer(customerId, policyId) {
        return this.fetch(`/customers/${customerId}/policies/${policyId}`, { method: 'DELETE' });
    }

    async getExpiringCustomerPolicies(days = 30) {
        return this.fetch(`/customers/expiring-policies?days=${days}`);
    }

    async createCustomer(data) {
        return this.fetch('/customers', { method: 'POST', body: JSON.stringify(data) });
    }

    async updateCustomer(id, data) {
        return this.fetch(`/customers/${id}`, { method: 'PUT', body: JSON.stringify(data) });
    }

    async deleteCustomer(id) {
        return this.fetch(`/customers/${id}`, { method: 'DELETE' });
    }

    // Policies
    async getPolicies(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.fetch(`/policies${query ? `?${query}` : ''}`);
    }

    async getPolicy(id) {
        return this.fetch(`/policies/${id}`);
    }

    async getPolicyDetails(id) {
        return this.fetch(`/policies/${id}/details`);
    }

    async getExpiringPolicies(days = 30) {
        return this.fetch(`/policies/expiring-soon?days=${days}`);
    }

    async createPolicy(data) {
        return this.fetch('/policies', { method: 'POST', body: JSON.stringify(data) });
    }

    async updatePolicy(id, data) {
        return this.fetch(`/policies/${id}`, { method: 'PUT', body: JSON.stringify(data) });
    }

    async renewPolicy(id, data = {}) {
        return this.fetch(`/policies/${id}/renew`, { method: 'POST', body: JSON.stringify(data) });
    }

    // Calls
    async getCalls(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.fetch(`/calls${query ? `?${query}` : ''}`);
    }

    async getCall(id) {
        return this.fetch(`/calls/${id}`);
    }

    async initiateCall(customerId) {
        return this.fetch(`/calls/initiate/${customerId}`, { method: 'POST' });
    }

    async updateCallSummary(id, data) {
        return this.fetch(`/calls/${id}/summary`, { method: 'PUT', body: JSON.stringify(data) });
    }

    async updateCallStatus(id, status) {
        return this.fetch(`/calls/${id}/status?status=${status}`, { method: 'PUT' });
    }

    async batchInitiateCalls(customerIds) {
        return this.fetch('/calls/batch', { method: 'POST', body: JSON.stringify({ customer_ids: customerIds }) });
    }

    // Analytics
    async getCallSummary(days = 30) {
        return this.fetch(`/analytics/calls/summary?days=${days}`);
    }

    async getCallOutcomes(days = 30) {
        return this.fetch(`/analytics/calls/outcomes?days=${days}`);
    }

    async getConversionRate(days = 30) {
        return this.fetch(`/analytics/conversion?days=${days}`);
    }

    async getDailyTrends(days = 7) {
        return this.fetch(`/analytics/daily?days=${days}`);
    }

    // Health Check
    async healthCheck() {
        return this.fetch('/health');
    }

    // Scheduler
    async getSchedulerConfig() {
        return this.fetch('/scheduler/config');
    }

    async updateSchedulerConfig(data) {
        return this.fetch('/scheduler/config', { method: 'PUT', body: JSON.stringify(data) });
    }

    async getSchedulerStats() {
        return this.fetch('/scheduler/stats');
    }

    async getPendingCustomers(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.fetch(`/scheduler/pending-customers${query ? `?${query}` : ''}`);
    }

    async getScheduledCalls(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.fetch(`/scheduler/scheduled-calls${query ? `?${query}` : ''}`);
    }

    async scheduleCall(data) {
        return this.fetch('/scheduler/scheduled-calls', { method: 'POST', body: JSON.stringify(data) });
    }

    async cancelScheduledCall(id) {
        return this.fetch(`/scheduler/scheduled-calls/${id}`, { method: 'DELETE' });
    }

    async triggerSchedulerNow(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.fetch(`/scheduler/trigger-now${query ? `?${query}` : ''}`, { method: 'POST' });
    }
}

export const api = new ApiClient();
export default api;

