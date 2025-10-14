import httpClient from './httpClient';
import { retryWithBackoff } from '../utils/retry';

class SatelliteService {
  /**
   * Search for satellites by name or NORAD ID
   * @param {string} query - Search query (name or NORAD ID)
   * @returns {Promise<Array>} Array of matching satellites
   */
  async searchSatellites(query) {
    try {
      const response = await retryWithBackoff(() => 
        httpClient.get('/satellites/search', {
          params: { query },
        })
      );
      return response.data.satellites || [];
    } catch (error) {
      const message = error.response?.data?.error?.message || 
                     error.response?.data?.detail || 
                     error.message || 
                     'Failed to search satellites';
      throw new Error(message);
    }
  }

  /**
   * Get satellite information by NORAD ID
   * @param {number} noradId - NORAD ID of the satellite
   * @returns {Promise<Object>} Satellite information with current position
   */
  async getSatelliteInfo(noradId) {
    try {
      const response = await httpClient.get(`/satellites/${noradId}`);
      return response.data;
    } catch (error) {
      const message = error.response?.data?.error?.message || 
                     error.response?.data?.detail || 
                     error.message || 
                     'Failed to get satellite information';
      throw new Error(message);
    }
  }

  /**
   * Get upcoming passes for a specific satellite
   * @param {number} noradId - NORAD ID of the satellite
   * @returns {Promise<Array>} Array of upcoming passes
   */
  async getSatellitePasses(noradId) {
    try {
      const response = await httpClient.get(`/satellites/${noradId}/passes`);
      return response.data.passes || [];
    } catch (error) {
      const message = error.response?.data?.error?.message || 
                     error.response?.data?.detail || 
                     error.message || 
                     'Failed to get satellite passes';
      throw new Error(message);
    }
  }

  /**
   * Get current position of a satellite
   * @param {number} noradId - NORAD ID of the satellite
   * @returns {Promise<Object>} Current satellite position
   */
  async getSatellitePosition(noradId) {
    try {
      const response = await httpClient.get(`/satellites/${noradId}/position`);
      return response.data;
    } catch (error) {
      const message = error.response?.data?.error?.message || 
                     error.response?.data?.detail || 
                     error.message || 
                     'Failed to get satellite position';
      throw new Error(message);
    }
  }

  /**
   * Get positions for multiple satellites
   * @param {Array<number>} noradIds - Array of NORAD IDs
   * @returns {Promise<Array>} Array of satellite positions
   */
  async getMultipleSatellitePositions(noradIds) {
    try {
      const promises = noradIds.map(id => this.getSatellitePosition(id));
      const results = await Promise.allSettled(promises);
      
      return results
        .filter(result => result.status === 'fulfilled')
        .map(result => result.value);
    } catch (error) {
      const message = error.message || 'Failed to get satellite positions';
      throw new Error(message);
    }
  }
}

const satelliteServiceInstance = new SatelliteService();
export default satelliteServiceInstance;