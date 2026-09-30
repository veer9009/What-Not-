import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { DemoProvider } from './state/DemoContext';
import App from './App';
import './styles/index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode><BrowserRouter><DemoProvider><App /></DemoProvider></BrowserRouter></React.StrictMode>
);

