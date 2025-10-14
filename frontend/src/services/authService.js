import httpClient from './httpClient';
import config from '../config';

class AuthService {
  /**
   * Register a new user
   * @param {string} email - User email
   * @param {string} password - User password
   * @param {string} confirmPassword - Password confirmation
   * @returns {Promise<Object>} User data and token
   */
  async register(email, password, confirmPassword) {
    try {
      const response = await httpClient.post('/auth/register', {
        email,
        password,
        confirm_password: confirmPassword,
      });

      const { access_token, user } = response.data;
      
      // Store token in localStorage
      localStorage.setItem(config.JWT_TOKEN_KEY, access_token);
      
      return { token: access_token, user };
    } catch (error) {
      // Extract error message from response
      const message = error.response?.data?.error?.message || 
                     error.response?.data?.detail || 
                     error.message || 
                     'Registration failed';
      throw new Error(message);
    }
  }

  /**
   * Login user
   * @param {string} email - User email
   * @param {string} password - User password
   * @returns {Promise<Object>} User data and token
   */
  async login(email, password) {
    try {
      const response = await httpClient.post('/auth/login', {
        email,
        password,
      });

      const { access_token, user } = response.data;
      
      // Store token in localStorage
      localStorage.setItem(config.JWT_TOKEN_KEY, access_token);
      
      return { token: access_token, user };
    } catch (error) {
      // Extract error message from response
      const message = error.response?.data?.error?.message || 
                     error.response?.data?.detail || 
                     error.message || 
                     'Login failed';
      throw new Error(message);
    }
  }

  /**
   * Logout user
   */
  logout() {
    localStorage.removeItem(config.JWT_TOKEN_KEY);
  }

  /**
   * Get current user profile
   * @returns {Promise<Object>} User profile data
   */
  async getCurrentUser() {
    try {
      const response = await httpClient.get('/auth/me');
      return response.data;
    } catch (error) {
      const message = error.response?.data?.error?.message || 
                     error.response?.data?.detail || 
                     error.message || 
                     'Failed to get user profile';
      throw new Error(message);
    }
  }

  /**
   * Check if user is authenticated
   * @returns {boolean} Authentication status
   */
  isAuthenticated() {
    const token = localStorage.getItem(config.JWT_TOKEN_KEY);
    if (!token) return false;

    try {
      // Check if token is expired
      const tokenData = JSON.parse(atob(token.split('.')[1]));
      const currentTime = Date.now() / 1000;
      return tokenData.exp > currentTime;
    } catch (error) {
      // Invalid token format
      localStorage.removeItem(config.JWT_TOKEN_KEY);
      return false;
    }
  }

  /**
   * Get stored token
   * @returns {string|null} JWT token
   */
  getToken() {
    return localStorage.getItem(config.JWT_TOKEN_KEY);
  }
}

const authServiceInstance = new AuthService();
export default authServiceInstance;