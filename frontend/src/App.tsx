import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import HomePage from './pages/HomePage';
import ChooseAvatarPage from './pages/ChooseAvatarPage';
import SessionPage from './pages/SessionPage';
import { ROUTES } from './config/constants';

function App() {
  return (
    <Router>
      <Routes>
        <Route path={ROUTES.HOME} element={<HomePage />} />
        <Route path={ROUTES.CHOOSE_AVATAR} element={<ChooseAvatarPage />} />
        <Route path={ROUTES.SESSION} element={<SessionPage />} />
      </Routes>
    </Router>
  );
}

export default App;
