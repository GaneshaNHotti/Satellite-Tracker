import React, { useState, useEffect } from 'react';
import satelliteService from '../services/satelliteService';
import userService from '../services/userService';

const SatelliteDetail = ({ satellite, onClose, onFavoriteToggled }) => {
  const [detailData, setDetailData] = useState(null);
  const [passes, setPasses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [passesLoading, setPassesLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isFavorite, setIsFavorite] = useState(false);
  const [favoriteId, setFavoriteId] = useState(null);

  useEffect(() => {
    if (satellite) {
      loadSatelliteDetail();
      checkIfFavorite();
    }
  }, [satellite]); // eslint-disable-line react-hooks/exhaustive-deps

  const loadSatelliteDetail = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const data = await satelliteService.getSatelliteInfo(satellite.norad_id);
      setDetailData(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const loadPasses = async () => {
    try {
      setPassesLoading(true);
      const passData = await satelliteService.getSatellitePasses(satellite.norad_id);
      setPasses(passData);
    } catch (err) {
      setError(`Failed to load passes: ${err.message}`);
    } finally {
      setPassesLoading(false);
    }
  };

  const checkIfFavorite = async () => {
    try {
      const favorites = await userService.getFavorites();
      const favorite = favorites.find(fav => fav.norad_id === satellite.norad_id);
      setIsFavorite(!!favorite);
      setFavoriteId(favorite?.id || null);
    } catch (err) {
      console.error('Failed to check favorite status:', err);
    }
  };

  const handleToggleFavorite = async () => {
    try {
      if (isFavorite) {
        await userService.removeFavorite(favoriteId);
        setIsFavorite(false);
        setFavoriteId(null);
      } else {
        const result = await userService.addFavorite(satellite.norad_id);
        setIsFavorite(true);
        setFavoriteId(result.id);
      }
      
      if (onFavoriteToggled) {
        onFavoriteToggled(satellite, !isFavorite);
      }
    } catch (err) {
      setError(`Failed to ${isFavorite ? 'remove from' : 'add to'} favorites: ${err.message}`);
    }
  };

  const formatPosition = (position) => {
    if (!position) return null;
    
    const lat = parseFloat(position.latitude).toFixed(6);
    const lng = parseFloat(position.longitude).toFixed(6);
    const alt = parseFloat(position.altitude).toFixed(1);
    const vel = parseFloat(position.velocity).toFixed(2);
    
    return { lat, lng, alt, vel };
  };

  const formatPassTime = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  const formatDuration = (seconds) => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds}s`;
  };

  const getVisibilityBadge = (visibility) => {
    const badgeClass = visibility === 'visible' ? 'bg-success' : 
                      visibility === 'daylight' ? 'bg-warning' : 'bg-secondary';
    return <span className={`badge ${badgeClass}`}>{visibility}</span>;
  };

  if (!satellite) return null;

  return (
    <div className="satellite-detail">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h4>{satellite.name}</h4>
        <button
          type="button"
          className="btn-close"
          onClick={onClose}
          aria-label="Close"
        ></button>
      </div>

      {error && (
        <div className="alert alert-danger" role="alert">
          {error}
        </div>
      )}

      {loading ? (
        <div className="d-flex justify-content-center my-4">
          <div className="spinner-border" role="status">
            <span className="visually-hidden">Loading satellite details...</span>
          </div>
        </div>
      ) : (
        <>
          <div className="row mb-4">
            <div className="col-md-8">
              <div className="card">
                <div className="card-header">
                  <h6 className="mb-0">Satellite Information</h6>
                </div>
                <div className="card-body">
                  <dl className="row">
                    <dt className="col-sm-4">NORAD ID:</dt>
                    <dd className="col-sm-8">{detailData?.norad_id || satellite.norad_id}</dd>
                    
                    <dt className="col-sm-4">Name:</dt>
                    <dd className="col-sm-8">{detailData?.name || satellite.name}</dd>
                    
                    {(detailData?.category || satellite.category) && (
                      <>
                        <dt className="col-sm-4">Category:</dt>
                        <dd className="col-sm-8">{detailData?.category || satellite.category}</dd>
                      </>
                    )}
                    
                    {(detailData?.country || satellite.country) && (
                      <>
                        <dt className="col-sm-4">Country:</dt>
                        <dd className="col-sm-8">{detailData?.country || satellite.country}</dd>
                      </>
                    )}
                    
                    {(detailData?.launch_date || satellite.launch_date) && (
                      <>
                        <dt className="col-sm-4">Launch Date:</dt>
                        <dd className="col-sm-8">
                          {new Date(detailData?.launch_date || satellite.launch_date).toLocaleDateString()}
                        </dd>
                      </>
                    )}
                  </dl>
                </div>
              </div>
            </div>
            
            <div className="col-md-4">
              <div className="card">
                <div className="card-header">
                  <h6 className="mb-0">Actions</h6>
                </div>
                <div className="card-body">
                  <button
                    type="button"
                    className={`btn ${isFavorite ? 'btn-success' : 'btn-outline-success'} w-100 mb-2`}
                    onClick={handleToggleFavorite}
                  >
                    {isFavorite ? '✓ Remove from Favorites' : '+ Add to Favorites'}
                  </button>
                  
                  <button
                    type="button"
                    className="btn btn-outline-primary w-100"
                    onClick={loadPasses}
                    disabled={passesLoading}
                  >
                    {passesLoading ? 'Loading...' : 'Load Pass Predictions'}
                  </button>
                </div>
              </div>
            </div>
          </div>

          {detailData?.current_position && (
            <div className="card mb-4">
              <div className="card-header">
                <h6 className="mb-0">Current Position</h6>
              </div>
              <div className="card-body">
                {(() => {
                  const pos = formatPosition(detailData.current_position);
                  return pos ? (
                    <div className="row">
                      <div className="col-md-3">
                        <strong>Latitude:</strong><br />
                        {pos.lat}°
                      </div>
                      <div className="col-md-3">
                        <strong>Longitude:</strong><br />
                        {pos.lng}°
                      </div>
                      <div className="col-md-3">
                        <strong>Altitude:</strong><br />
                        {pos.alt} km
                      </div>
                      <div className="col-md-3">
                        <strong>Velocity:</strong><br />
                        {pos.vel} km/s
                      </div>
                      <div className="col-12 mt-2">
                        <small className="text-muted">
                          Last updated: {new Date(detailData.current_position.timestamp).toLocaleString()}
                        </small>
                      </div>
                    </div>
                  ) : (
                    <p className="text-muted">Position data unavailable</p>
                  );
                })()}
              </div>
            </div>
          )}

          {passes.length > 0 && (
            <div className="card">
              <div className="card-header">
                <h6 className="mb-0">Upcoming Passes ({passes.length})</h6>
              </div>
              <div className="card-body">
                <div className="table-responsive">
                  <table className="table table-sm">
                    <thead>
                      <tr>
                        <th>Start Time</th>
                        <th>Duration</th>
                        <th>Max Elevation</th>
                        <th>Visibility</th>
                        <th>Magnitude</th>
                      </tr>
                    </thead>
                    <tbody>
                      {passes.map((pass, index) => (
                        <tr key={index}>
                          <td>{formatPassTime(pass.start_time)}</td>
                          <td>{formatDuration(pass.duration)}</td>
                          <td>{parseFloat(pass.max_elevation).toFixed(1)}°</td>
                          <td>{getVisibilityBadge(pass.visibility)}</td>
                          <td>
                            {pass.magnitude ? parseFloat(pass.magnitude).toFixed(1) : 'N/A'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {passesLoading && (
            <div className="d-flex justify-content-center my-3">
              <div className="spinner-border" role="status">
                <span className="visually-hidden">Loading passes...</span>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default SatelliteDetail;