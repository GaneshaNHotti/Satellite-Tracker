import React, { useState, useEffect } from 'react';
import userService from '../services/userService';

const FavoritesList = ({ onSatelliteSelect, onFavoriteRemoved, refreshTrigger }) => {
  const [favorites, setFavorites] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const loadFavorites = async (showRefreshing = false) => {
    try {
      if (showRefreshing) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }
      setError(null);

      const favs = await userService.getFavorites();
      setFavorites(favs);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadFavorites();
  }, [refreshTrigger]);

  const handleRemoveFavorite = async (favorite) => {
    try {
      await userService.removeFavorite(favorite.id);
      setFavorites(prev => prev.filter(fav => fav.id !== favorite.id));
      if (onFavoriteRemoved) {
        onFavoriteRemoved(favorite);
      }
    } catch (err) {
      setError(`Failed to remove ${favorite.name} from favorites: ${err.message}`);
    }
  };

  const formatPosition = (position) => {
    if (!position) return 'Position unavailable';
    
    const lat = parseFloat(position.latitude).toFixed(4);
    const lng = parseFloat(position.longitude).toFixed(4);
    const alt = parseFloat(position.altitude).toFixed(1);
    const vel = parseFloat(position.velocity).toFixed(2);
    
    return `${lat}°, ${lng}° • ${alt} km • ${vel} km/s`;
  };

  const formatTimestamp = (timestamp) => {
    if (!timestamp) return '';
    return new Date(timestamp).toLocaleString();
  };

  if (loading) {
    return (
      <div className="d-flex justify-content-center my-4">
        <div className="spinner-border" role="status">
          <span className="visually-hidden">Loading favorites...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="favorites-list">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h5 className="mb-0">My Favorite Satellites ({favorites.length})</h5>
        <button
          type="button"
          className="btn btn-outline-secondary btn-sm"
          onClick={() => loadFavorites(true)}
          disabled={refreshing}
        >
          {refreshing ? (
            <>
              <span className="spinner-border spinner-border-sm me-1" role="status"></span>
              Refreshing...
            </>
          ) : (
            '🔄 Refresh Positions'
          )}
        </button>
      </div>

      {error && (
        <div className="alert alert-danger" role="alert">
          {error}
        </div>
      )}

      {favorites.length === 0 ? (
        <div className="alert alert-info">
          <h6>No favorite satellites yet</h6>
          <p className="mb-0">
            Use the search above to find satellites and add them to your favorites.
          </p>
        </div>
      ) : (
        <div className="row">
          {favorites.map((favorite) => (
            <div key={favorite.id} className="col-md-6 col-lg-4 mb-3">
              <div className="card h-100">
                <div className="card-body">
                  <div className="d-flex justify-content-between align-items-start mb-2">
                    <h6 className="card-title mb-0">{favorite.name}</h6>
                    <button
                      type="button"
                      className="btn btn-outline-danger btn-sm"
                      onClick={() => handleRemoveFavorite(favorite)}
                      title="Remove from favorites"
                    >
                      ×
                    </button>
                  </div>
                  
                  <p className="card-text">
                    <small className="text-muted">
                      NORAD ID: {favorite.norad_id}
                      {favorite.category && (
                        <>
                          <br />
                          Category: {favorite.category}
                        </>
                      )}
                    </small>
                  </p>

                  {favorite.current_position ? (
                    <div className="mb-2">
                      <strong>Current Position:</strong>
                      <br />
                      <small className="text-muted">
                        {formatPosition(favorite.current_position)}
                      </small>
                      <br />
                      <small className="text-muted">
                        Updated: {formatTimestamp(favorite.current_position.timestamp)}
                      </small>
                    </div>
                  ) : (
                    <div className="mb-2">
                      <small className="text-warning">
                        Position data unavailable
                      </small>
                    </div>
                  )}

                  <div className="d-flex gap-2">
                    <button
                      type="button"
                      className="btn btn-primary btn-sm flex-grow-1"
                      onClick={() => onSatelliteSelect && onSatelliteSelect(favorite)}
                    >
                      View Details
                    </button>
                  </div>
                </div>
                
                <div className="card-footer">
                  <small className="text-muted">
                    Added: {new Date(favorite.added_at).toLocaleDateString()}
                  </small>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default FavoritesList;