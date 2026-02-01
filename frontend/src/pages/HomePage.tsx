import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../config/constants';
import { AnimatedOrb } from '../components/AnimatedOrb';

function HomePage() {
  const navigate = useNavigate();
  const [isMobile, setIsMobile] = useState(window.innerWidth < 640);

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth < 640);
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const handleStart = () => {
    navigate(ROUTES.CHOOSE_AVATAR);
  };

  return (
    <div
      className="min-h-screen bg-white flex items-center justify-center p-4 relative overflow-hidden cursor-pointer"
      onClick={handleStart}
      role="button"
      tabIndex={0}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          handleStart();
        }
      }}
    >
      <div className="relative z-10 flex flex-col items-center justify-center h-full px-4">
        <div className="mb-6 orb-intro">
          <AnimatedOrb size={isMobile ? 180 : 256} />
        </div>
        <p className="text-xl sm:text-2xl font-medium text-stone-400 mb-2 text-center">
          Appointment Assistant
        </p>
        <p className="text-sm text-stone-400 text-center">
          {isMobile ? 'Tap' : 'Click'} anywhere to get started
        </p>

      </div>
    </div>
  );
}

export default HomePage;
