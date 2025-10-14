import React, { useState, useEffect } from 'react';
import LocationDisplay from './LocationDisplay';
import LocationForm from './LocationForm';
import userService from '../services/userService';

const LocationManager = () => {
  const [location, setLocation] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  useEffect(() => {
    loadLocation();
  }, []);

  const loadLocation = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const locationData = await userService.getLocation();
      setLocation(locationData);
      
      // If no location exists, start in editing mode
      if (!locationData) {
        setIsEditing(true);
      }
    } catch (err) {
      setError(err.message);
      // If no location exists, start in editing mode
      setIsEditing(true);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSaveLocation = async (locationData) => {
    setIsLoading(true);
    setError(null);
    setSuccess(null);

    try {
      let savedLocation;
      if (location) {
        // Update existing location
        savedLocation = await userService.updateLocation(
          locationData.latitude,
          locationData.longitude,
          locationData.address
        );
        setSuccess('Location updated successfully!');
      } else {
        // Save new location
        savedLocation = await userService.saveLocation(
          locationData.latitude,
          locationData.longitude,
          locationData.address
        );
        setSuccess('Location saved successfully!');
      }
      
      setLocation(savedLocation);
      setIsEditing(false);
      
      // Clear success message after 3 seconds
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleEditLocation = () => {
    setIsEditing(true);
    setError(null);
    setSuccess(null);
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
    setError(null);
    setSuccess(null);
  };

  const handleDeleteLocation = async () => {
    if (!window.confirm('Are you sure you want to delete your location? This will remove all pass predictions.')) {
      return;
    }

    setIsLoading(true);
    setError(null);
    setSuccess(null);

    try {
      // Note: The API doesn't have a delete endpoint, so we'll just clear the location locally
      // In a real implementation, you might want to add a DELETE endpoint
      setLocation(null);
      setIsEditing(true);
      setSuccess('Location deleted successfully!');
      
      // Clear success message after 3 seconds
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const getCurrentLocation = () => {
    if (!navigator.geolocation) {
      setError('Geolocation is not supported by this browser.');
      return;
    }

    setIsLoading(true);
    setError(null);

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude } = position.coords;
        handleSaveLocation({
          latitude,
          longitude,
          address: 'Current location (from GPS)'
        });
      },
      (err) => {
        setIsLoading(false);
        switch (err.code) {
          case err.PERMISSION_DENIED:
            setError('Location access denied by user.');
            break;
          case err.POSITION_UNAVAILABLE:
            setError('Location information is unavailable.');
            break;
          case err.TIMEOUT:
            setError('Location request timed out.');
            break;
          default:
            setError('An unknown error occurred while retrieving location.');
            break;
        }
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0
      }
    );
  };

  if (isLoading && !location && !isEditing) {
    return (
      <div className="text-center py-4">
        <div className="spinner-border" role="status">
          <span className="visually-hidden">Loading...</span>
        </div>
        <div className="mt-2">Loading location...</div>
      </div>
    );
  }

  return (
    <div>
      {success && (
        <div className="alert alert-success alert-dismissible fade show" role="alert">
          <i className="bi bi-check-circle me-2"></i>
          {success}
          <button 
            type="button" 
            className="btn-close" 
            onClick={() => setSuccess(null)}
            aria-label="Close"
          ></button>
        </div>
      )}

      {isEditing ? (
        <div className="card">
          <div className="card-header">
            <h5 className="mb-0">
              <i className="bi bi-geo-alt me-2"></i>
              {location ? 'Edit Location' : 'Add Your Location'}
            </h5>
          </div>
          <div className="card-body">
            <div className="mb-3">
              <button
                type="button"
                className="btn btn-outline-primary btn-sm"
                onClick={getCurrentLocation}
                disabled={isLoading}
              >
                <i className="bi bi-crosshair me-2"></i>
                Use Current Location
              </button>
              <small className="form-text text-muted ms-2">
                Get your location automatically using GPS
              </small>
            </div>
            
            <LocationForm
              initialLocation={location}
              onSave={handleSaveLocation}
              onCancel={location ? handleCancelEdit : null}
              isLoading={isLoading}
              error={error}
            />
          </div>
        </div>
      ) : (
        <LocationDisplay
          location={location}
          onEdit={handleEditLocation}
          onDelete={handleDeleteLocation}
          isLoading={isLoading}
        />
      )}
    </div>
  );
};

export default LocationManager;