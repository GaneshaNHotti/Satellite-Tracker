import React, { useState, useEffect, useCallback } from 'react';
import satelliteService from '../services/satelliteService';
import userService from '../services/userService';

const SatelliteSearch = ({ onSatelliteSelect, onFavoriteAdded }) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [favorites, setFavorites] = useState([]);

  // Load favorites to check which satellites are already favorited
  useEffect(() => {
    const loadFavorites = async () => {
      try {
        const favs = await userService.getFavorites();
        setFavorites(favs.map(fav => fav.norad_id));
      } catch (err) {
        console.error('Failed to load favorites:', err);
      }
    };
    loadFavorites();
  }, []);

  // Debounced search function
  const performSearch = useCallback(async (searchQuery) => {
    if (!searchQuery.trim()) {
      setResults([]);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const satellites = await satelliteService.searchSatellites(searchQuery);
      setResults(satellites);
    } catch (err) {
      setError(err.message);
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  // Debounce search input
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      performSearch(query);
    }, 300);

    return () => clearTimeout(timeoutId);
  }, [query, performSearch]);

  const handleAddToFavorites = async (satellite) => {
    try {
      await userService.addFavorite(satellite.norad_id);
      setFavorites(prev => [...prev, satellite.norad_id]);
      if (onFavoriteAdded) {
        onFavoriteAdded(satellite);
      }
    } catch (err) {
      setError(`Failed to add ${satellite.name} to favorites: ${err.message}`);
    }
  };

  const isFavorite = (noradId) => favorites.includes(noradId);

  return (
    <div className="satellite-search">
      <div className="mb-3">
        <label htmlFor="satellite-search-input" className="form-label">
          Search Satellites
        </label>
        <input
          id="satellite-search-input"
          type="text"
          className="form-control"
          placeholder="Enter satellite name or NORAD ID..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <div className="form-text">
          Search by satellite name (e.g., "ISS") or NORAD ID (e.g., "25544")
        </div>
      </div>

      {error && (
        <div className="alert alert-danger" role="alert">
          {error}
        </div>
      )}

      {loading && (
        <div className="d-flex justify-content-center my-3">
          <div className="spinner-border" role="status">
            <span className="visually-hidden">Searching...</span>
          </div>
        </div>
      )}

      {results.length > 0 && (
        <div className="search-results">
          <h6>Search Results ({results.length})</h6>
          <div className="list-group">
            {results.map((satellite) => (
              <div
                key={satellite.norad_id}
                className="list-group-item list-group-item-action"
              >
                <div className="d-flex w-100 justify-content-between align-items-start">
                  <div className="flex-grow-1">
                    <h6 className="mb-1">{satellite.name}</h6>
                    <p className="mb-1 text-muted">
                      NORAD ID: {satellite.norad_id}
                      {satellite.category && ` • Category: ${satellite.category}`}
                      {satellite.country && ` • Country: ${satellite.country}`}
                    </p>
                    {satellite.launch_date && (
                      <small className="text-muted">
                        Launched: {new Date(satellite.launch_date).toLocaleDateString()}
                      </small>
                    )}
                  </div>
                  <div className="btn-group" role="group">
                    <button
                      type="button"
                      className="btn btn-outline-primary btn-sm"
                      onClick={() => onSatelliteSelect && onSatelliteSelect(satellite)}
                    >
                      View Details
                    </button>
                    {!isFavorite(satellite.norad_id) ? (
                      <button
                        type="button"
                        className="btn btn-outline-success btn-sm"
                        onClick={() => handleAddToFavorites(satellite)}
                      >
                        Add to Favorites
                      </button>
                    ) : (
                      <button
                        type="button"
                        className="btn btn-success btn-sm"
                        disabled
                      >
                        ✓ Favorited
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {query.trim() && !loading && results.length === 0 && !error && (
        <div className="alert alert-info">
          No satellites found matching "{query}". Try a different search term.
        </div>
      )}
    </div>
  );
};

export default SatelliteSearch;