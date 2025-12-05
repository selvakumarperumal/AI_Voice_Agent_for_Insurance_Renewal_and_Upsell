import { NavLink } from 'react-router-dom';

function Sidebar() {
    return (
        <aside className="sidebar">
            <div className="sidebar-logo">
                <div className="logo-icon">🎙️</div>
                <h1>InsureVoice AI</h1>
            </div>

            <nav className="sidebar-nav">
                <div className="nav-section">
                    <span className="nav-section-title">Main</span>
                    <NavLink to="/" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
                        <span className="icon">📊</span>
                        Dashboard
                    </NavLink>
                </div>

                <div className="nav-section">
                    <span className="nav-section-title">Management</span>
                    <NavLink to="/customers" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
                        <span className="icon">👥</span>
                        Customers
                    </NavLink>
                    <NavLink to="/products" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
                        <span className="icon">📦</span>
                        Products
                    </NavLink>
                    <NavLink to="/policies" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
                        <span className="icon">📋</span>
                        Policies
                    </NavLink>
                </div>

                <div className="nav-section">
                    <span className="nav-section-title">Voice Agent</span>
                    <NavLink to="/calls" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
                        <span className="icon">📞</span>
                        Calls
                    </NavLink>
                    <NavLink to="/scheduler" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
                        <span className="icon">📅</span>
                        Scheduler
                    </NavLink>
                </div>
            </nav>

            <div className="sidebar-footer" style={{ marginTop: 'auto', padding: '1rem', borderTop: '1px solid var(--border-color)' }}>
                <div className="flex items-center gap-md">
                    <div className="avatar">AI</div>
                    <div>
                        <div className="font-medium text-sm">Voice Agent</div>
                        <div className="text-muted text-sm">Online</div>
                    </div>
                </div>
            </div>
        </aside>
    );
}

export default Sidebar;
