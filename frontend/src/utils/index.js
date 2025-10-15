// Utility functions for the application

/**
 * Format date for display
 * @param {string|Date} date - Date to format
 * @returns {string} Formatted date string
 */
export const formatDate = (date) => {
  if (!date) return '';
  const d = new Date(date);
  return d.toLocaleDateString() + ' ' + d.toLocaleTimeString();
};

/**
 * Format coordinates for display
 * @param {number} lat - Latitude
 * @param {number} lng - Longitude
 * @returns {string} Formatted coordinates
 */
export const formatCoordinates = (lat, lng) => {
  if (lat === undefined || lng === undefined) return '';
  return `${lat.toFixed(4)}°, ${lng.toFixed(4)}°`;
};

/**
 * Validate email format
 * @param {string} email - Email to validate
 * @returns {boolean} True if valid email format
 */
export const isValidEmail = (email) => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
};

/**
 * Validate password strength
 * @param {string} password - Password to validate
 * @returns {object} Validation result with isValid and message
 */
export const validatePassword = (password) => {
  if (!password) {
    return { isValid: false, message: 'Password is required' };
  }
  
  if (password.length < 8) {
    return { isValid: false, message: 'Password must be at least 8 characters long' };
  }
  
  // Check for at least one uppercase letter
  if (!/[A-Z]/.test(password)) {
    return { isValid: false, message: 'Password must contain at least one uppercase letter' };
  }
  
  // Check for at least one lowercase letter
  if (!/[a-z]/.test(password)) {
    return { isValid: false, message: 'Password must contain at least one lowercase letter' };
  }
  
  // Check for at least one digit
  if (!/\d/.test(password)) {
    return { isValid: false, message: 'Password must contain at least one digit' };
  }
  
  return { isValid: true, message: '' };
};

/**
 * Validate latitude and longitude
 * @param {number} lat - Latitude
 * @param {number} lng - Longitude
 * @returns {object} Validation result
 */
export const validateCoordinates = (lat, lng) => {
  const errors = {};
  
  if (lat === undefined || lat === null || lat === '') {
    errors.latitude = 'Latitude is required';
  } else if (isNaN(lat) || lat < -90 || lat > 90) {
    errors.latitude = 'Latitude must be between -90 and 90';
  }
  
  if (lng === undefined || lng === null || lng === '') {
    errors.longitude = 'Longitude is required';
  } else if (isNaN(lng) || lng < -180 || lng > 180) {
    errors.longitude = 'Longitude must be between -180 and 180';
  }
  
  return {
    isValid: Object.keys(errors).length === 0,
    errors
  };
};