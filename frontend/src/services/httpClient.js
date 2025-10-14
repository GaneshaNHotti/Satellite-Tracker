import axios from 'axios';
import config from '../config';

// Create axios instance with base configuration
const httpClient = axios.create({
  baseURL: config.API_URL,
  timeout: 30000, // 30 seconds timeout
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add authentication token
httpClient.interceptors.request.use(
  (requestConfig) => {
    const token = localStorage.getItem(config.JWT_TOKEN_KEY);
    if (token) {
      requestConfig.headers.Authorization = `Bearer ${token}`;
    }
    return requestConfig;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling and token refresh
httpClient.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error) => {
    const originalRequest = error.config;

    // Handle 401 Unauthorized errors
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      // Remove invalid token
      localStorage.removeItem(config.JWT_TOKEN_KEY);
      
      // Redirect to login page
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
      
      return Promise.reject(error);
    }

    // Handle network errors
    if (!error.response) {
      error.message = 'Network error. Please check your internet connection.';
    }

    // Handle server errors
    if (error.response?.status >= 500) {
      error.message = 'Server error. Please try again later.';
    }

    // Handle rate limiting
    if (error.response?.status === 429) {
      error.message = 'Too many requests. Please wait a moment and try again.';
    }

    return Promise.reject(error);
  }
);

export default httpClient;