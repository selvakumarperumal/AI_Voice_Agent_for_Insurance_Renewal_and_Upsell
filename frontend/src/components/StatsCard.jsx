function StatsCard({ icon, value, label, change, changeType }) {
    return (
        <div className="stat-card">
            <div className="stat-icon">{icon}</div>
            <div className="stat-value">{value}</div>
            <div className="stat-label">{label}</div>
            {change !== undefined && (
                <div className={`stat-change ${changeType || 'positive'}`}>
                    {changeType === 'negative' ? '↓' : '↑'} {change}
                </div>
            )}
        </div>
    );
}

export default StatsCard;
