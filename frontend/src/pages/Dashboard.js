import React, { useState } from 'react';
import { SatelliteManager } from '../components';
import SatelliteTrackingDashboard from '../components/SatelliteTrackingDashboard';

const Dashboard = () => {
  const [activeView, setActiveView] = useState('dashboard');

  return (
    <div className="row">
      <div className="col-12">
        {/* Navigation Tabs */}
        <ul className="nav nav-tabs mb-4" role="tablist">
          <li className="nav-item" role="presentation">
            <button
              className={`nav-link ${activeView === 'dashboard' ? 'active' : ''}`}
              onClick={() => setActiveView('dashboard')}
              type="button"
              role="tab"
            >
              📊 Tracking Dashboard
            </button>
          </li>
          <li className="nav-item" role="presentation">
            <button
              className={`nav-link ${activeView === 'manage' ? 'active' : ''}`}
              onClick={() => setActiveView('manage')}
              type="button"
              role="tab"
            >
              🛰️ Manage Satellites
            </button>
          </li>
        </ul>

        {/* Tab Content */}
        <div className="tab-content">
          {activeView === 'dashboard' && (
            <div className="tab-pane fade show active">
              <SatelliteTrackingDashboard />
            </div>
          )}

          {activeView === 'manage' && (
            <div className="tab-pane fade show active">
              <div className="mb-4">
                <h3>Satellite Management</h3>
                <p className="text-muted">
                  Search for satellites, manage your favorites, and view detailed information.
                </p>
              </div>
              <SatelliteManager />
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;