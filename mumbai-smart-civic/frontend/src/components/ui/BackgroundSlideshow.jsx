import { useState, useEffect } from 'react';

const IMAGES = [
  '/auth-bg/media__1773675445341.jpg',
  '/auth-bg/media__1773675445401.jpg',
  '/auth-bg/media__1773675445451.jpg',
  '/auth-bg/media__1773675445522.jpg',
];

// Each slide is visible for this long (ms) before cross-fading to the next
const SLIDE_DURATION = 5000;
// Cross-fade duration — must match the CSS transition
const FADE_DURATION = 1200;

export default function BackgroundSlideshow() {
  const [current, setCurrent] = useState(0);
  const [next, setNext] = useState(1);
  const [fading, setFading] = useState(false);

  useEffect(() => {
    const timer = setInterval(() => {
      // Start the cross-fade
      setFading(true);

      // After the fade completes, snap the current image forward
      const fadeTimer = setTimeout(() => {
        setCurrent((prev) => (prev + 1) % IMAGES.length);
        setNext((prev) => (prev + 1) % IMAGES.length);
        setFading(false);
      }, FADE_DURATION);

      return () => clearTimeout(fadeTimer);
    }, SLIDE_DURATION);

    return () => clearInterval(timer);
  }, []);

  const baseStyle = {
    position: 'fixed',
    inset: 0,
    width: '100%',
    height: '100%',
    backgroundSize: 'cover',
    backgroundPosition: 'center center',
    backgroundRepeat: 'no-repeat',
    willChange: 'opacity',
  };

  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 0, pointerEvents: 'none' }}>
      {/* Bottom layer — always the NEXT image so it shows through during fade */}
      <div
        style={{
          ...baseStyle,
          backgroundImage: `url(${IMAGES[next]})`,
          opacity: 1,
          zIndex: 1,
        }}
      />

      {/* Top layer — current image that fades OUT */}
      <div
        style={{
          ...baseStyle,
          backgroundImage: `url(${IMAGES[current]})`,
          opacity: fading ? 0 : 1,
          transition: fading ? `opacity ${FADE_DURATION}ms ease-in-out` : 'none',
          zIndex: 2,
        }}
      />

      {/* Subtle dark overlay for legibility */}
      <div
        style={{
          ...baseStyle,
          background: 'rgba(0, 0, 0, 0.45)',
          zIndex: 3,
        }}
      />
    </div>
  );
}
