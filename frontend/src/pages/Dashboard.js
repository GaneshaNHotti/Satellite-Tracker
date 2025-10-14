import React from 'react';
import { SatelliteManager } from '../components';

const Dashboard = () => {
  return (
    <div className="row">
      <div className="col-12">
        <h2>Satellite Tracking Dashboard</h2>
        <p className="text-muted mb-4">
          Search for satellites, manage your favorites, and track their positions in real-time.
        </p>
        
        <SatelliteManager />
      </div>
    </div>
  );
};

export default Dashboard;