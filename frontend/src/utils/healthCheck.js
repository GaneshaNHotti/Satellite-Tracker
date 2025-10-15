/**
 * Health check utilities for backend connectivity
 */

import httpClient from '../services/httpClient';

/**
 * Check if the backend is reachable
 * @returns {Promise<boolean>} True if backend is healthy
 */
export const checkBackendHealth = async () => {
  try {
    const response = await httpClient.get('/health');
    console.log(response);
    return response.status === 200 && response.data.status === 'healthy';
  } catch (error) {
    console.error('Backend health check failed:', error.message);
    return false;
  }
};

/**
 * Get detailed backend health information
 * @returns {Promise<Object|null>} Health details or null if unavailable
 */
export const getBackendHealthDetails = async () => {
  try {
    const response = await httpClient.get('/health/detailed');
    return response.data;
  } catch (error) {
    console.error('Detailed health check failed:', error.message);
    return null;
  }
};

/**
 * Check if specific API endpoints are available
 * @returns {Promise<Object>} Object with endpoint availability status
 */
export const checkAPIEndpoints = async () => {
  const endpoints = {
    auth: '/api/v1/auth/me',
    favorites: '/api/v1/users/favorites', 
    passes: '/api/v1/users/passes',
    location: '/api/v1/users/location'
  };
  
  const results = {};
  
  for (const [name, endpoint] of Object.entries(endpoints)) {
    try {
      // Make a HEAD request to check if endpoint exists
      await httpClient.head(endpoint);
      results[name] = { available: true, status: 'ok' };
    } catch (error) {
      results[name] = { 
        available: false, 
        status: error.response?.status || 'unreachable',
        error: error.message 
      };
    }
  }
  
  return results;
};