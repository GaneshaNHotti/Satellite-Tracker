import React from 'react';

const Home = () => {
  return (
    <div className="row">
      <div className="col-12">
        <div className="jumbotron bg-primary text-white p-5 rounded mb-4">
          <h1 className="display-4">Welcome to Satellite Tracker</h1>
          <p className="lead">
            Track satellites in real-time and get alerts for passes over your location.
          </p>
          <hr className="my-4" />
          <p>
            Register for an account to start tracking your favorite satellites and receive 
            personalized pass predictions for your location.
          </p>
        </div>
        
        <div className="row">
          <div className="col-md-4">
            <div className="card h-100">
              <div className="card-body">
                <h5 className="card-title">Real-time Tracking</h5>
                <p className="card-text">
                  Get current positions of satellites with live updates every few minutes.
                </p>
              </div>
            </div>
          </div>
          <div className="col-md-4">
            <div className="card h-100">
              <div className="card-body">
                <h5 className="card-title">Pass Predictions</h5>
                <p className="card-text">
                  See when satellites will pass over your location with detailed timing and visibility info.
                </p>
              </div>
            </div>
          </div>
          <div className="col-md-4">
            <div className="card h-100">
              <div className="card-body">
                <h5 className="card-title">Favorites Management</h5>
                <p className="card-text">
                  Save your favorite satellites for quick access and personalized tracking.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Home;