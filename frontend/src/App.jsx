import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Students from './pages/Students';
import Rooms from './pages/Rooms';
import Exams from './pages/Exams';
import Seating from './pages/Seating';
import TestAPI from './pages/TestAPI';

function App() {
  return (
    <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="students" element={<Students />} />
          <Route path="rooms" element={<Rooms />} />
          <Route path="exams" element={<Exams />} />
          <Route path="seating" element={<Seating />} />
          <Route path="test" element={<TestAPI />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
