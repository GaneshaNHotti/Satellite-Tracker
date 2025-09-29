import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import './App.css';

function App() {
  return (
    <Router>
      <div className="App">
        <header className="App-header">
          <h1>Satellite Tracker & Alerts Platform</h1>
        </header>
        <main className="container mt-4">
          <Routes>
            <Route path="/" element={<Home />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

function Home() {
  return (
    <div className="row">
      <div className="col-12">
        <h2>Welcome to Satellite Tracker</h2>
        <p>Track satellites in real-time and get alerts for passes over your location.</p>
      </div>
    </div>
  );
}

export default App;