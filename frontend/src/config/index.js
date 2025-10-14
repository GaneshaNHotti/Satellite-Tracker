// Application configuration
const config = {
  // API Configuration
  API_BASE_URL: process.env.REACT_APP_API_URL || 'http://localhost:8000',
  API_VERSION: 'v1',
  
  // Get full API URL with version
  get API_URL() {
    return `${this.API_BASE_URL}/api/${this.API_VERSION}`;
  },
  
  // Authentication
  JWT_TOKEN_KEY: 'satellite_tracker_token',
  
  // Cache settings
  POSITION_REFRESH_INTERVAL: 5 * 60 * 1000, // 5 minutes in milliseconds
  PASS_CACHE_DURATION: 24 * 60 * 60 * 1000, // 24 hours in milliseconds
  
  // Application settings
  APP_NAME: 'Satellite Tracker & Alerts Platform',
  APP_VERSION: '1.0.0',
};

export default config;