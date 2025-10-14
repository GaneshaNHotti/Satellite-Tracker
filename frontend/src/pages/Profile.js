import React from 'react';
import { LocationManager } from '../components';

const Profile = () => {
  return (
    <div className="row">
      <div className="col-md-8">
        <div className="mb-4">
          <h2 className="mb-3">User Profile</h2>
          <LocationManager />
        </div>
        
        <div className="card">
          <div className="card-header">
            <h5 className="mb-0">Account Settings</h5>
          </div>
          <div className="card-body">
            <div className="alert alert-info">
              <i className="bi bi-info-circle me-2"></i>
              Additional profile features like account settings and preferences will be implemented in future updates.
            </div>
          </div>
        </div>
      </div>
      
      <div className="col-md-4">
        <div className="card">
          <div className="card-header">
            <h6 className="mb-0">Location Tips</h6>
          </div>
          <div className="card-body">
            <ul className="list-unstyled mb-0">
              <li className="mb-2">
                <i className="bi bi-lightbulb text-warning me-2"></i>
                <small>Use precise coordinates for accurate pass predictions</small>
              </li>
              <li className="mb-2">
                <i className="bi bi-shield-check text-success me-2"></i>
                <small>Your location is stored securely and used only for satellite tracking</small>
              </li>
              <li className="mb-0">
                <i className="bi bi-arrow-clockwise text-info me-2"></i>
                <small>Update your location if you move to get relevant predictions</small>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Profile;