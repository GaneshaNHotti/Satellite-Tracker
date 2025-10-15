import React, { useState, useEffect, useCallback } from 'react';
import userService from '../services/userService';
import { checkBackendHealth } from '../utils/healthCheck';

const SatelliteTrackingDashboard = () => {
  const [favorites, setFavorites] = useState([]);
  const [passes, setPasses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [passesLoading, setPassesLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [backendHealthy, setBackendHealthy] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshInterval, setRefreshInterval] = useState(null);
  
  // Filtering and sorting state
  const [satelliteFilter, setSatelliteFilter] = useState('');
  const [satelliteSort, setSatelliteSort] = useState('name');
  const [passFilter, setPassFilter] = useState('all');
  const [passSort, setPassSort] = useState('start_time');
  const [showOnlyVisible, setShowOnlyVisible] = useState(false);

  // Load initial data
  useEffect(() => {
    loadDashboardData();
  }, []);

  // Auto-refresh setup
  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(() => {
        refreshPositions();
      }, 5 * 60 * 1000); // Refresh every 5 minutes
      
      setRefreshInterval(interval);
      return () => clearInterval(interval);
    } else if (refreshInterval) {
      clearInterval(refreshInterval);
      setRefreshInterval(null);
    }
  }, [autoRefresh]); // eslint-disable-line react-hooks/exhaustive-deps

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Check backend health first
      const isHealthy = await checkBackendHealth();
      setBackendHealthy(isHealthy);
      
      if (!isHealthy) {
        setError('Backend service is not available. Please check if the server is running.');
        setFavorites([]);
        setPasses([]);
        return;
      }
      
      // Load favorites and passes in parallel
      const [favoritesData, passesData] = await Promise.allSettled([
        userService.getFavorites(),
        userService.getUpcomingPasses()
      ]);

      if (favoritesData.status === 'fulfilled') {
        setFavorites(favoritesData.value);
      } else {
        console.error('Failed to load favorites:', favoritesData.reason);
        // Set empty array for favorites if failed
        setFavorites([]);
      }

      if (passesData.status === 'fulfilled') {
        setPasses(passesData.value);
      } else {
        console.error('Failed to load passes:', passesData.reason);
        // Set empty array for passes if failed (likely no location or favorites set)
        setPasses([]);
      }

      setLastUpdate(new Date());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const refreshPositions = async () => {
    if (favorites.length === 0) return;
    
    try {
      setRefreshing(true);
      const updatedFavorites = await userService.getFavorites();
      setFavorites(updatedFavorites);
      setLastUpdate(new Date());
    } catch (err) {
      console.error('Failed to refresh positions:', err);
    } finally {
      setRefreshing(false);
    }
  };

  const refreshPasses = async () => {
    try {
      setPassesLoading(true);
      const passesData = await userService.getUpcomingPasses();
      setPasses(passesData);
    } catch (err) {
      setError(`Failed to refresh passes: ${err.message}`);
    } finally {
      setPassesLoading(false);
    }
  };

  // Filter and sort satellites
  const filteredAndSortedSatellites = useCallback(() => {
    let filtered = favorites.filter(satellite => 
      satellite.name.toLowerCase().includes(satelliteFilter.toLowerCase()) ||
      satellite.norad_id.toString().includes(satelliteFilter)
    );

    filtered.sort((a, b) => {
      switch (satelliteSort) {
        case 'name':
          return a.name.localeCompare(b.name);
        case 'norad_id':
          return a.norad_id - b.norad_id;
        case 'altitude':
          const altA = a.current_position?.altitude || 0;
          const altB = b.current_position?.altitude || 0;
          return altB - altA; // Highest first
        case 'velocity':
          const velA = a.current_position?.velocity || 0;
          const velB = b.current_position?.velocity || 0;
          return velB - velA; // Fastest first
        case 'added_at':
          return new Date(b.added_at) - new Date(a.added_at); // Newest first
        default:
          return 0;
      }
    });

    return filtered;
  }, [favorites, satelliteFilter, satelliteSort]);

  // Filter and sort passes
  const filteredAndSortedPasses = useCallback(() => {
    let filtered = passes;

    // Filter by visibility
    if (showOnlyVisible) {
      filtered = filtered.filter(pass => pass.visibility === 'visible');
    }

    // Filter by elevation
    if (passFilter !== 'all') {
      const minElevation = parseInt(passFilter);
      filtered = filtered.filter(pass => pass.max_elevation >= minElevation);
    }

    // Sort passes
    filtered.sort((a, b) => {
      switch (passSort) {
        case 'start_time':
          return new Date(a.start_time) - new Date(b.start_time);
        case 'elevation':
          return b.max_elevation - a.max_elevation; // Highest first
        case 'duration':
          return b.duration - a.duration; // Longest first
        case 'satellite':
          return a.satellite.name.localeCompare(b.satellite.name);
        default:
          return 0;
      }
    });

    return filtered;
  }, [passes, passFilter, passSort, showOnlyVisible]);

  const formatPosition = (position) => {
    if (!position) return 'Position unavailable';
    
    const lat = parseFloat(position.latitude).toFixed(4);
    const lng = parseFloat(position.longitude).toFixed(4);
    const alt = parseFloat(position.altitude).toFixed(1);
    const vel = parseFloat(position.velocity).toFixed(2);
    
    return { lat, lng, alt, vel };
  };

  const formatPassTime = (dateString) => {
    const date = new Date(dateString);
    return {
      date: date.toLocaleDateString(),
      time: date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };
  };

  const formatDuration = (seconds) => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds}s`;
  };

  const getVisibilityBadge = (visibility) => {
    const badgeClass = visibility === 'visible' ? 'bg-success' : 
                      visibility === 'daylight' ? 'bg-warning text-dark' : 'bg-secondary';
    return <span className={`badge ${badgeClass}`}>{visibility}</span>;
  };

  const getElevationColor = (elevation) => {
    if (elevation >= 60) return 'text-success';
    if (elevation >= 30) return 'text-warning';
    return 'text-muted';
  };

  if (loading) {
    return (
      <div className="d-flex justify-content-center my-5">
        <div className="spinner-border" role="status">
          <span className="visually-hidden">Loading dashboard...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="satellite-tracking-dashboard">
      {/* Dashboard Header */}
      <div className="row mb-4">
        <div className="col-12">
          <div className="d-flex justify-content-between align-items-center">
            <div>
              <h2>Satellite Tracking Dashboard</h2>
              <p className="text-muted mb-0">
                Real-time tracking of your favorite satellites and upcoming passes
              </p>
            </div>
            <div className="d-flex gap-2">
              <div className="form-check form-switch">
                <input
                  className="form-check-input"
                  type="checkbox"
                  id="autoRefresh"
                  checked={autoRefresh}
                  onChange={(e) => setAutoRefresh(e.target.checked)}
                />
                <label className="form-check-label" htmlFor="autoRefresh">
                  Auto-refresh
                </label>
              </div>
              <button
                type="button"
                className="btn btn-outline-primary btn-sm"
                onClick={refreshPositions}
                disabled={refreshing}
              >
                {refreshing ? (
                  <>
                    <span className="spinner-border spinner-border-sm me-1"></span>
                    Refreshing...
                  </>
                ) : (
                  '🔄 Refresh Positions'
                )}
              </button>
            </div>
          </div>
          {lastUpdate && (
            <small className="text-muted">
              Last updated: {lastUpdate.toLocaleString()}
            </small>
          )}
        </div>
      </div>
      {/* Satellites Section */}
      <div className="row mb-5">
        <div className="col-12">
          <div className="card">
            <div className="card-header">
              <div className="d-flex justify-content-between align-items-center">
                <h5 className="mb-0">
                  Favorite Satellites ({filteredAndSortedSatellites().length})
                </h5>
                <div className="d-flex gap-2">
                  <input
                    type="text"
                    className="form-control form-control-sm"
                    placeholder="Filter satellites..."
                    value={satelliteFilter}
                    onChange={(e) => setSatelliteFilter(e.target.value)}
                    style={{ width: '200px' }}
                  />
                  <select
                    className="form-select form-select-sm"
                    value={satelliteSort}
                    onChange={(e) => setSatelliteSort(e.target.value)}
                    style={{ width: '150px' }}
                  >
                    <option value="name">Sort by Name</option>
                    <option value="norad_id">Sort by NORAD ID</option>
                    <option value="altitude">Sort by Altitude</option>
                    <option value="velocity">Sort by Velocity</option>
                    <option value="added_at">Sort by Date Added</option>
                  </select>
                </div>
              </div>
            </div>
            <div className="card-body">
              {filteredAndSortedSatellites().length === 0 ? (
                <div className="alert alert-info">
                  <h6>No satellites found</h6>
                  <p className="mb-0">
                    {favorites.length === 0 
                      ? 'Add some satellites to your favorites to see them here.'
                      : 'No satellites match your current filter.'}
                  </p>
                </div>
              ) : (
                <div className="table-responsive">
                  <table className="table table-hover">
                    <thead>
                      <tr>
                        <th>Satellite</th>
                        <th>NORAD ID</th>
                        <th>Position</th>
                        <th>Altitude</th>
                        <th>Velocity</th>
                        <th>Last Update</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredAndSortedSatellites().map((satellite) => {
                        const pos = formatPosition(satellite.current_position);
                        return (
                          <tr key={satellite.id}>
                            <td>
                              <div>
                                <strong>{satellite.name}</strong>
                                {satellite.category && (
                                  <>
                                    <br />
                                    <small className="text-muted">{satellite.category}</small>
                                  </>
                                )}
                              </div>
                            </td>
                            <td>{satellite.norad_id}</td>
                            <td>
                              {pos !== 'Position unavailable' ? (
                                <small>
                                  {pos.lat}°, {pos.lng}°
                                </small>
                              ) : (
                                <span className="text-warning">Unavailable</span>
                              )}
                            </td>
                            <td>
                              {pos !== 'Position unavailable' ? (
                                `${pos.alt} km`
                              ) : (
                                <span className="text-muted">-</span>
                              )}
                            </td>
                            <td>
                              {pos !== 'Position unavailable' ? (
                                `${pos.vel} km/s`
                              ) : (
                                <span className="text-muted">-</span>
                              )}
                            </td>
                            <td>
                              {satellite.current_position?.timestamp ? (
                                <small className="text-muted">
                                  {new Date(satellite.current_position.timestamp).toLocaleString()}
                                </small>
                              ) : (
                                <span className="text-muted">-</span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Passes Section */}
      <div className="row">
        <div className="col-12">
          <div className="card">
            <div className="card-header">
              <div className="d-flex justify-content-between align-items-center">
                <h5 className="mb-0">
                  Upcoming Passes ({filteredAndSortedPasses().length})
                </h5>
                <div className="d-flex gap-2">
                  <div className="form-check form-check-inline">
                    <input
                      className="form-check-input"
                      type="checkbox"
                      id="visibleOnly"
                      checked={showOnlyVisible}
                      onChange={(e) => setShowOnlyVisible(e.target.checked)}
                    />
                    <label className="form-check-label" htmlFor="visibleOnly">
                      Visible only
                    </label>
                  </div>
                  <select
                    className="form-select form-select-sm"
                    value={passFilter}
                    onChange={(e) => setPassFilter(e.target.value)}
                    style={{ width: '180px' }}
                  >
                    <option value="all">All elevations</option>
                    <option value="10">Min 10° elevation</option>
                    <option value="30">Min 30° elevation</option>
                    <option value="60">Min 60° elevation</option>
                  </select>
                  <select
                    className="form-select form-select-sm"
                    value={passSort}
                    onChange={(e) => setPassSort(e.target.value)}
                    style={{ width: '150px' }}
                  >
                    <option value="start_time">Sort by Time</option>
                    <option value="elevation">Sort by Elevation</option>
                    <option value="duration">Sort by Duration</option>
                    <option value="satellite">Sort by Satellite</option>
                  </select>
                  <button
                    type="button"
                    className="btn btn-outline-secondary btn-sm"
                    onClick={refreshPasses}
                    disabled={passesLoading}
                  >
                    {passesLoading ? (
                      <>
                        <span className="spinner-border spinner-border-sm me-1"></span>
                        Loading...
                      </>
                    ) : (
                      '🔄 Refresh Passes'
                    )}
                  </button>
                </div>
              </div>
            </div>
            <div className="card-body">
              {filteredAndSortedPasses().length === 0 ? (
                <div className="alert alert-info">
                  <h6>No upcoming passes found</h6>
                  <p className="mb-0">
                    {passes.length === 0 
                      ? 'No passes predicted for your favorite satellites in the next 10 days.'
                      : 'No passes match your current filters.'}
                  </p>
                </div>
              ) : (
                <div className="table-responsive">
                  <table className="table table-hover">
                    <thead>
                      <tr>
                        <th>Satellite</th>
                        <th>Date</th>
                        <th>Start Time</th>
                        <th>Duration</th>
                        <th>Max Elevation</th>
                        <th>Visibility</th>
                        <th>Magnitude</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredAndSortedPasses().map((pass, index) => {
                        const passTime = formatPassTime(pass.start_time);
                        return (
                          <tr key={index}>
                            <td>
                              <strong>{pass.satellite.name}</strong>
                              <br />
                              <small className="text-muted">
                                NORAD {pass.satellite.norad_id}
                              </small>
                            </td>
                            <td>{passTime.date}</td>
                            <td>{passTime.time}</td>
                            <td>{formatDuration(pass.duration)}</td>
                            <td>
                              <span className={getElevationColor(pass.max_elevation)}>
                                <strong>{parseFloat(pass.max_elevation).toFixed(1)}°</strong>
                              </span>
                            </td>
                            <td>{getVisibilityBadge(pass.visibility)}</td>
                            <td>
                              {pass.magnitude ? (
                                <span className="text-muted">
                                  {parseFloat(pass.magnitude).toFixed(1)}
                                </span>
                              ) : (
                                <span className="text-muted">N/A</span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SatelliteTrackingDashboard;