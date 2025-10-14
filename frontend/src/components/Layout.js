import React from 'react';
import Navigation from './Navigation';

const Layout = ({ children }) => {
  return (
    <div className="min-vh-100 d-flex flex-column">
      <Navigation />
      <main className="container mt-4 flex-grow-1">
        {children}
      </main>
      <footer className="bg-light py-3 mt-5">
        <div className="container text-center">
          <small className="text-muted">
            © 2024 Satellite Tracker Platform. Powered by N2YO API.
          </small>
        </div>
      </footer>
    </div>
  );
};

export default Layout;