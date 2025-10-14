import React from 'react';

const LocationDisplay = ({ location, onEdit, onDelete, isLoading = false }) => {
  if (!location) {
    return (
      <div className="alert alert-info" role="alert">
        <i className="bi bi-info-circle me-2"></i>
        No location saved. Please add your location to get satellite pass predictions.
      </div>
    );
  }

  const formatCoordinate = (value, type) => {
    const num = parseFloat(value);
    const direction = type === 'latitude' 
      ? (num >= 0 ? 'N' : 'S')
      : (num >= 0 ? 'E' : 'W');
    return `${Math.abs(num).toFixed(6)}° ${direction}`;
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  return (
    <div className="card">
      <div className="card-header d-flex justify-content-between align-items-center">
        <h5 className="mb-0">
          <i className="bi bi-geo-alt me-2"></i>
          Your Location
        </h5>
        <div className="btn-group" role="group">
          <button
            type="button"
            className="btn btn-outline-primary btn-sm"
            onClick={onEdit}
            disabled={isLoading}
            title="Edit location"
          >
            <i className="bi bi-pencil"></i>
          </button>
          {onDelete && (
            <button
              type="button"
              className="btn btn-outline-danger btn-sm"
              onClick={onDelete}
              disabled={isLoading}
              title="Delete location"
            >
              <i className="bi bi-trash"></i>
            </button>
          )}
        </div>
      </div>
      
      <div className="card-body">
        <div className="row">
          <div className="col-md-6">
            <div className="mb-3">
              <label className="form-label text-muted small">Latitude</label>
              <div className="fw-bold">
                {formatCoordinate(location.latitude, 'latitude')}
              </div>
            </div>
          </div>
          
          <div className="col-md-6">
            <div className="mb-3">
              <label className="form-label text-muted small">Longitude</label>
              <div className="fw-bold">
                {formatCoordinate(location.longitude, 'longitude')}
              </div>
            </div>
          </div>
        </div>

        {location.address && (
          <div className="mb-3">
            <label className="form-label text-muted small">Address</label>
            <div className="fw-bold">
              <i className="bi bi-house me-2"></i>
              {location.address}
            </div>
          </div>
        )}

        <div className="row">
          <div className="col-md-6">
            <div className="mb-2">
              <label className="form-label text-muted small">Added</label>
              <div className="small">
                {formatDate(location.created_at)}
              </div>
            </div>
          </div>
          
          {location.updated_at && location.updated_at !== location.created_at && (
            <div className="col-md-6">
              <div className="mb-2">
                <label className="form-label text-muted small">Last Updated</label>
                <div className="small">
                  {formatDate(location.updated_at)}
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="mt-3 p-2 bg-light rounded">
          <small className="text-muted">
            <i className="bi bi-info-circle me-1"></i>
            This location is used to calculate satellite pass predictions for your area.
          </small>
        </div>
      </div>
    </div>
  );
};

export default LocationDisplay;