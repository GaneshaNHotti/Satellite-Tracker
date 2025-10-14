import React, { useState } from 'react';
import SatelliteSearch from './SatelliteSearch';
import FavoritesList from './FavoritesList';
import SatelliteDetail from './SatelliteDetail';

const SatelliteManager = () => {
  const [selectedSatellite, setSelectedSatellite] = useState(null);
  const [showDetail, setShowDetail] = useState(false);
  const [activeTab, setActiveTab] = useState('search');
  const [favoritesRefreshTrigger, setFavoritesRefreshTrigger] = useState(0);

  const handleSatelliteSelect = (satellite) => {
    setSelectedSatellite(satellite);
    setShowDetail(true);
  };

  const handleCloseDetail = () => {
    setShowDetail(false);
    setSelectedSatellite(null);
  };

  const handleFavoriteAdded = (satellite) => {
    // Refresh favorites list
    setFavoritesRefreshTrigger(prev => prev + 1);
    // Show success message or switch to favorites tab
    setActiveTab('favorites');
  };

  const handleFavoriteRemoved = (favorite) => {
    // Refresh favorites list is handled by the component itself
    // Could show a success message here if needed
  };

  const handleFavoriteToggled = (satellite, isNowFavorite) => {
    // Refresh favorites list when toggled from detail view
    setFavoritesRefreshTrigger(prev => prev + 1);
  };

  if (showDetail && selectedSatellite) {
    return (
      <div className="satellite-manager">
        <SatelliteDetail
          satellite={selectedSatellite}
          onClose={handleCloseDetail}
          onFavoriteToggled={handleFavoriteToggled}
        />
      </div>
    );
  }

  return (
    <div className="satellite-manager">
      <div className="row mb-4">
        <div className="col-12">
          <h3>Satellite Management</h3>
          <p className="text-muted">
            Search for satellites, manage your favorites, and view detailed information.
          </p>
        </div>
      </div>

      {/* Tab Navigation */}
      <ul className="nav nav-tabs mb-4" role="tablist">
        <li className="nav-item" role="presentation">
          <button
            className={`nav-link ${activeTab === 'search' ? 'active' : ''}`}
            onClick={() => setActiveTab('search')}
            type="button"
            role="tab"
          >
            🔍 Search Satellites
          </button>
        </li>
        <li className="nav-item" role="presentation">
          <button
            className={`nav-link ${activeTab === 'favorites' ? 'active' : ''}`}
            onClick={() => setActiveTab('favorites')}
            type="button"
            role="tab"
          >
            ⭐ My Favorites
          </button>
        </li>
      </ul>

      {/* Tab Content */}
      <div className="tab-content">
        {activeTab === 'search' && (
          <div className="tab-pane fade show active">
            <SatelliteSearch
              onSatelliteSelect={handleSatelliteSelect}
              onFavoriteAdded={handleFavoriteAdded}
            />
          </div>
        )}

        {activeTab === 'favorites' && (
          <div className="tab-pane fade show active">
            <FavoritesList
              onSatelliteSelect={handleSatelliteSelect}
              onFavoriteRemoved={handleFavoriteRemoved}
              refreshTrigger={favoritesRefreshTrigger}
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default SatelliteManager;