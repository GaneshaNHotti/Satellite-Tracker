import httpClient from './httpClient';

class UserService {
  /**
   * Get user's saved location
   * @returns {Promise<Object>} Location data
   */
  async getLocation() {
    try {
      const response = await httpClient.get('/users/location');
      return response.data;
    } catch (error) {
      // Handle 404 as no location saved
      if (error.response?.status === 404) {
        return null;
      }
      
      const message = error.response?.data?.error?.message || 
                     error.response?.data?.detail || 
                     error.message || 
                     'Failed to get location';
      throw new Error(message);
    }
  }

  /**
   * Save user's location
   * @param {number} latitude - Latitude coordinate
   * @param {number} longitude - Longitude coordinate
   * @param {string} address - Optional address description
   * @returns {Promise<Object>} Saved location data
   */
  async saveLocation(latitude, longitude, address = null) {
    try {
      const response = await httpClient.post('/users/location', {
        latitude,
        longitude,
        address,
      });
      return response.data;
    } catch (error) {
      const message = error.response?.data?.error?.message || 
                     error.response?.data?.detail || 
                     error.message || 
                     'Failed to save location';
      throw new Error(message);
    }
  }

  /**
   * Update user's location
   * @param {number} latitude - Latitude coordinate
   * @param {number} longitude - Longitude coordinate
   * @param {string} address - Optional address description
   * @returns {Promise<Object>} Updated location data
   */
  async updateLocation(latitude, longitude, address = null) {
    try {
      const response = await httpClient.put('/users/location', {
        latitude,
        longitude,
        address,
      });
      return response.data;
    } catch (error) {
      const message = error.response?.data?.error?.message || 
                     error.response?.data?.detail || 
                     error.message || 
                     'Failed to update location';
      throw new Error(message);
    }
  }

  /**
   * Get user's favorite satellites
   * @returns {Promise<Array>} Array of favorite satellites with current positions
   */
  async getFavorites() {
    try {
      const response = await httpClient.get('/users/favorites');
      return response.data.favorites || [];
    } catch (error) {
      // Handle specific error cases more gracefully
      if (error.response?.status === 404) {
        // Endpoint not found - likely backend not running or routing issue
        console.warn('Favorites endpoint not found - backend may not be running');
        return [];
      }
      
      const message = error.response?.data?.error?.message || 
                     error.response?.data?.detail || 
                     error.message || 
                     'Failed to get favorites';
      throw new Error(message);
    }
  }

  /**
   * Add satellite to favorites
   * @param {number} noradId - NORAD ID of the satellite
   * @returns {Promise<Object>} Added favorite data
   */
  async addFavorite(noradId) {
    try {
      const response = await httpClient.post('/users/favorites', {
        norad_id: noradId,
      });
      return response.data;
    } catch (error) {
      const message = error.response?.data?.error?.message || 
                     error.response?.data?.detail || 
                     error.message || 
                     'Failed to add favorite';
      throw new Error(message);
    }
  }

  /**
   * Remove satellite from favorites
   * @param {number} favoriteId - ID of the favorite record
   * @returns {Promise<void>}
   */
  async removeFavorite(favoriteId) {
    try {
      await httpClient.delete(`/users/favorites/${favoriteId}`);
    } catch (error) {
      const message = error.response?.data?.error?.message || 
                     error.response?.data?.detail || 
                     error.message || 
                     'Failed to remove favorite';
      throw new Error(message);
    }
  }

  /**
   * Get upcoming passes for all favorite satellites
   * @returns {Promise<Array>} Array of upcoming passes
   */
  async getUpcomingPasses() {
    try {
      const response = await httpClient.get('/users/passes');
      return response.data.passes || [];
    } catch (error) {
      // Handle specific error cases more gracefully
      if (error.response?.status === 404) {
        // Endpoint not found - likely backend not running or routing issue
        console.warn('Passes endpoint not found - backend may not be running');
        return [];
      }
      
      if (error.response?.status === 422) {
        // Validation error - likely no location set
        console.warn('Cannot get passes - user may need to set location first');
        return [];
      }
      
      const message = error.response?.data?.error?.message || 
                     error.response?.data?.detail || 
                     error.message || 
                     'Failed to get upcoming passes';
      throw new Error(message);
    }
  }
}

const userServiceInstance = new UserService();
export default userServiceInstance;