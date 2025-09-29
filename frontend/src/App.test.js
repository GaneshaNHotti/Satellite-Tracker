import { render, screen } from '@testing-library/react';
import App from './App';

test('renders satellite tracker heading', () => {
  render(<App />);
  const linkElement = screen.getByText(/Satellite Tracker & Alerts Platform/i);
  expect(linkElement).toBeInTheDocument();
});