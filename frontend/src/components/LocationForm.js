import React, { useState } from 'react';

const LocationForm = ({ 
  initialLocation = null, 
  onSave, 
  onCancel, 
  isLoading = false,
  error = null 
}) => {
  const [formData, setFormData] = useState({
    latitude: initialLocation?.latitude || '',
    longitude: initialLocation?.longitude || '',
    address: initialLocation?.address || ''
  });
  
  const [validationErrors, setValidationErrors] = useState({});

  const validateCoordinate = (value, type) => {
    const num = parseFloat(value);
    if (isNaN(num)) {
      return `${type} must be a valid number`;
    }
    
    if (type === 'Latitude') {
      if (num < -90 || num > 90) {
        return 'Latitude must be between -90 and 90 degrees';
      }
    } else if (type === 'Longitude') {
      if (num < -180 || num > 180) {
        return 'Longitude must be between -180 and 180 degrees';
      }
    }
    
    return null;
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));

    // Clear validation error for this field
    if (validationErrors[name]) {
      setValidationErrors(prev => ({
        ...prev,
        [name]: null
      }));
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    
    // Validate coordinates
    const errors = {};
    const latError = validateCoordinate(formData.latitude, 'Latitude');
    const lngError = validateCoordinate(formData.longitude, 'Longitude');
    
    if (latError) errors.latitude = latError;
    if (lngError) errors.longitude = lngError;
    
    if (!formData.latitude.trim()) {
      errors.latitude = 'Latitude is required';
    }
    if (!formData.longitude.trim()) {
      errors.longitude = 'Longitude is required';
    }

    setValidationErrors(errors);

    if (Object.keys(errors).length === 0) {
      onSave({
        latitude: parseFloat(formData.latitude),
        longitude: parseFloat(formData.longitude),
        address: formData.address.trim() || null
      });
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      {error && (
        <div className="alert alert-danger" role="alert">
          <strong>Error:</strong> {error}
        </div>
      )}
      
      <div className="row">
        <div className="col-md-6">
          <div className="mb-3">
            <label htmlFor="latitude" className="form-label">
              Latitude <span className="text-danger">*</span>
            </label>
            <input
              type="number"
              step="any"
              className={`form-control ${validationErrors.latitude ? 'is-invalid' : ''}`}
              id="latitude"
              name="latitude"
              value={formData.latitude}
              onChange={handleInputChange}
              placeholder="e.g., 40.7128"
              disabled={isLoading}
            />
            {validationErrors.latitude && (
              <div className="invalid-feedback">
                {validationErrors.latitude}
              </div>
            )}
            <div className="form-text">
              Valid range: -90 to 90 degrees
            </div>
          </div>
        </div>
        
        <div className="col-md-6">
          <div className="mb-3">
            <label htmlFor="longitude" className="form-label">
              Longitude <span className="text-danger">*</span>
            </label>
            <input
              type="number"
              step="any"
              className={`form-control ${validationErrors.longitude ? 'is-invalid' : ''}`}
              id="longitude"
              name="longitude"
              value={formData.longitude}
              onChange={handleInputChange}
              placeholder="e.g., -74.0060"
              disabled={isLoading}
            />
            {validationErrors.longitude && (
              <div className="invalid-feedback">
                {validationErrors.longitude}
              </div>
            )}
            <div className="form-text">
              Valid range: -180 to 180 degrees
            </div>
          </div>
        </div>
      </div>

      <div className="mb-3">
        <label htmlFor="address" className="form-label">
          Address (Optional)
        </label>
        <input
          type="text"
          className="form-control"
          id="address"
          name="address"
          value={formData.address}
          onChange={handleInputChange}
          placeholder="e.g., New York, NY, USA"
          disabled={isLoading}
        />
        <div className="form-text">
          Optional description of your location
        </div>
      </div>

      <div className="d-flex gap-2">
        <button 
          type="submit" 
          className="btn btn-primary"
          disabled={isLoading}
        >
          {isLoading ? (
            <>
              <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
              Saving...
            </>
          ) : (
            initialLocation ? 'Update Location' : 'Save Location'
          )}
        </button>
        
        {onCancel && (
          <button 
            type="button" 
            className="btn btn-secondary"
            onClick={onCancel}
            disabled={isLoading}
          >
            Cancel
          </button>
        )}
      </div>
    </form>
  );
};

export default LocationForm;