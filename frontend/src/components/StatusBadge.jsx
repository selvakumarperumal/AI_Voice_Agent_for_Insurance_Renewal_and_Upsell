function StatusBadge({ status, type = 'default' }) {
    const statusConfig = {
        // Call statuses
        completed: { class: 'badge-success', label: 'Completed' },
        in_progress: { class: 'badge-info', label: 'In Progress' },
        initiated: { class: 'badge-info', label: 'Initiated' },
        failed: { class: 'badge-error', label: 'Failed' },
        pending: { class: 'badge-warning', label: 'Pending' },

        // Policy statuses
        active: { class: 'badge-success', label: 'Active' },
        expired: { class: 'badge-error', label: 'Expired' },
        cancelled: { class: 'badge-error', label: 'Cancelled' },
        expiring: { class: 'badge-warning', label: 'Expiring Soon' },

        // Product statuses
        true: { class: 'badge-success', label: 'Active' },
        false: { class: 'badge-error', label: 'Inactive' },

        // Call outcomes
        interested: { class: 'badge-success', label: 'Interested' },
        not_interested: { class: 'badge-error', label: 'Not Interested' },
        callback: { class: 'badge-warning', label: 'Callback' },
        upsell_accepted: { class: 'badge-success', label: 'Upsell Accepted' },
        no_answer: { class: 'badge-default', label: 'No Answer' },

        // Product types
        Health: { class: 'badge-info', label: '🏥 Health' },
        Life: { class: 'badge-success', label: '💚 Life' },
        Motor: { class: 'badge-warning', label: '🚗 Motor' },
        Home: { class: 'badge-default', label: '🏠 Home' },
    };

    const config = statusConfig[status] || { class: 'badge-default', label: status };

    return (
        <span className={`badge ${config.class}`}>
            {config.label}
        </span>
    );
}

export default StatusBadge;
