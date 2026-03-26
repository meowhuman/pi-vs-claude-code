/**
 * CINEMATIC SPARKLE - Interactive Experience
 * Vanilla JavaScript - No dependencies
 */

(function() {
  'use strict';

  // ============================================
  // Configuration
  // ============================================
  
  const CONFIG = {
    particles: {
      stars: { count: 80, sizes: [1, 2, 3] },
      cloudSparkles: { count: 70, sizes: [2, 3, 4, 6] },
      foregroundSparkles: { count: 50, sizes: [3, 4, 5, 7, 8] }
    },
    colors: ['#FFFFFF', '#FFD700', '#00FFFF', '#FF69B4', '#9370DB'],
    parallax: {
      bg: 0.15,
      cloud: 0.35,
      foreground: 0.55,
      card: 0.42
    },
    animations: {
      twinkleMin: 2200,
      twinkleMax: 5800,
      floatMin: 9000,
      floatMax: 13000
    },
    reducedMotion: window.matchMedia('(prefers-reduced-motion: reduce)').matches,
    isMobile: window.innerWidth < 768
  };

  // Adjust particle count for mobile
  if (CONFIG.isMobile) {
    CONFIG.particles.stars.count = Math.floor(CONFIG.particles.stars.count * 0.55);
    CONFIG.particles.cloudSparkles.count = Math.floor(CONFIG.particles.cloudSparkles.count * 0.5);
    CONFIG.particles.foregroundSparkles.count = Math.floor(CONFIG.particles.foregroundSparkles.count * 0.5);
  }

  // ============================================
  // State
  // ============================================
  
  let scrollY = 0;
  let ticking = false;
  const layers = {};
  const glassCards = [];

  // ============================================
  // Utility Functions
  // ============================================
  
  const random = (min, max) => Math.random() * (max - min) + min;
  
  const randomInt = (min, max) => Math.floor(random(min, max));
  
  const randomChoice = (arr) => arr[Math.floor(Math.random() * arr.length)];
  
  const clamp = (val, min, max) => Math.min(Math.max(val, min), max);

  // ============================================
  // Particle Generation
  // ============================================
  
  function createSparkle(container, options) {
    const sparkle = document.createElement('div');
    sparkle.className = 'sparkle';
    
    const size = randomChoice(options.sizes);
    const color = randomChoice(CONFIG.colors);
    const duration = random(CONFIG.animations.twinkleMin, CONFIG.animations.twinkleMax);
    const delay = random(-duration, 0);
    
    sparkle.style.cssText = `
      width: ${size}px;
      height: ${size}px;
      left: ${random(0, 100)}%;
      top: ${random(0, 100)}%;
      background: ${color};
      color: ${color};
      animation: twinkle ${duration}ms ease-in-out ${delay}ms infinite;
    `;
    
    if (!CONFIG.reducedMotion) {
      sparkle.style.animation = `twinkle ${duration}ms ease-in-out ${delay}ms infinite, sparkleDrift ${random(4000, 8000)}ms ease-in-out ${random(-2000, 0)}ms infinite`;
    }
    
    container.appendChild(sparkle);
    return sparkle;
  }

  function createStar(container, options) {
    const star = document.createElement('div');
    star.className = 'star';
    
    const size = randomChoice(options.sizes);
    const duration = random(CONFIG.animations.twinkleMin, CONFIG.animations.twinkleMax);
    const delay = random(-duration, 0);
    
    star.style.cssText = `
      width: ${size}px;
      height: ${size}px;
      left: ${random(0, 100)}%;
      top: ${random(0, 60)}%;
      --twinkle-duration: ${duration}ms;
      animation-delay: ${delay}ms;
    `;
    
    // Vary opacity for depth
    star.style.opacity = random(0.2, 0.6);
    
    container.appendChild(star);
    return star;
  }

  function generateParticles() {
    // Generate background stars
    const starsContainer = document.getElementById('stars-bg');
    if (starsContainer) {
      const fragment = document.createDocumentFragment();
      for (let i = 0; i < CONFIG.particles.stars.count; i++) {
        createStar(fragment, CONFIG.particles.stars);
      }
      starsContainer.appendChild(fragment);
    }

    // Generate cloud sparkles
    const cloudContainer = document.getElementById('sparkle-cloud');
    if (cloudContainer) {
      const fragment = document.createDocumentFragment();
      for (let i = 0; i < CONFIG.particles.cloudSparkles.count; i++) {
        createSparkle(fragment, CONFIG.particles.cloudSparkles);
      }
      cloudContainer.appendChild(fragment);
    }

    // Generate foreground sparkles
    const foregroundContainer = document.getElementById('sparkle-foreground');
    if (foregroundContainer) {
      const fragment = document.createDocumentFragment();
      for (let i = 0; i < CONFIG.particles.foregroundSparkles.count; i++) {
        createSparkle(fragment, CONFIG.particles.foregroundSparkles);
      }
      foregroundContainer.appendChild(fragment);
    }
  }

  // ============================================
  // Parallax Engine
  // ============================================
  
  function initParallax() {
    // Store layer references
    const layerBg = document.querySelector('.layer-bg');
    const layerCloud = document.querySelector('.layer-cloud');
    const layerForeground = document.querySelector('.layer-foreground');
    
    if (layerBg) layers.bg = layerBg;
    if (layerCloud) layers.cloud = layerCloud;
    if (layerForeground) layers.foreground = layerForeground;
    
    // Store glass card references
    document.querySelectorAll('.glass-card').forEach(card => {
      const depth = parseFloat(card.dataset.depth) || CONFIG.parallax.card;
      glassCards.push({ element: card, depth });
    });
  }

  function updateParallax() {
    // Update layer transforms
    Object.keys(layers).forEach(key => {
      const layer = layers[key];
      const speed = CONFIG.parallax[key];
      const y = -scrollY * speed;
      
      // Use translate3d for GPU acceleration
      layer.style.transform = `translate3d(0, ${y}px, 0)`;
    });
    
    // Update glass card parallax (subtle offset) using CSS custom property
    // This preserves hover and reveal animations
    glassCards.forEach(card => {
      const cardY = -scrollY * card.depth;
      card.element.style.setProperty('--parallax-y', `${cardY}px`);
    });
  }

  function onScroll() {
    scrollY = window.pageYOffset;
    
    if (!ticking) {
      window.requestAnimationFrame(() => {
        if (!CONFIG.reducedMotion) {
          updateParallax();
        }
        ticking = false;
      });
      
      ticking = true;
    }
  }

  // ============================================
  // Intersection Observer for Reveals
  // ============================================
  
  function initRevealObserver() {
    if (CONFIG.reducedMotion) {
      // Show all cards immediately if reduced motion
      document.querySelectorAll('.glass-card').forEach(card => {
        card.classList.add('is-visible');
      });
      return;
    }

    const observerOptions = {
      threshold: 0.2,
      rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          // Optional: stop observing once revealed
          // observer.unobserve(entry.target);
        }
      });
    }, observerOptions);

    document.querySelectorAll('.glass-card').forEach(card => {
      observer.observe(card);
    });

    return observer;
  }

  // ============================================
  // Smooth Scroll for Anchor Links
  // ============================================
  
  function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
      anchor.addEventListener('click', function(e) {
        const href = this.getAttribute('href');
        if (href === '#') {
          e.preventDefault();
          return;
        }
        
        const target = document.querySelector(href);
        if (target) {
          e.preventDefault();
          target.scrollIntoView({
            behavior: CONFIG.reducedMotion ? 'auto' : 'smooth'
          });
        }
      });
    });
  }

  // ============================================
  // Responsive Adjustments
  // ============================================
  
  function handleResize() {
    const wasMobile = CONFIG.isMobile;
    CONFIG.isMobile = window.innerWidth < 768;
    
    // Only reinitialize if crossing mobile threshold
    if (wasMobile !== CONFIG.isMobile) {
      // Could add dynamic particle adjustment here if needed
      // For now, the initial count is sufficient
    }
  }

  // ============================================
  // Cloud Float Animation Duration
  // ============================================
  
  function randomizeCloudFloat() {
    const cloudCluster = document.querySelector('.cloud-cluster');
    if (cloudCluster) {
      const duration = random(CONFIG.animations.floatMin, CONFIG.animations.floatMax);
      cloudCluster.style.animationDuration = `${duration}ms`;
    }
  }

  // ============================================
  // Initialize
  // ============================================
  
  function init() {
    // Generate all particles
    generateParticles();
    
    // Initialize parallax
    initParallax();
    
    // Initial parallax update
    if (!CONFIG.reducedMotion) {
      updateParallax();
    }
    
    // Set up scroll listener
    window.addEventListener('scroll', onScroll, { passive: true });
    
    // Initialize reveal observer
    initRevealObserver();
    
    // Initialize smooth scroll
    initSmoothScroll();
    
    // Randomize cloud float duration
    randomizeCloudFloat();
    
    // Handle resize
    window.addEventListener('resize', handleResize, { passive: true });
    
    // Log initialization
    console.log('🌟 Cinematic Sparkle initialized');
    console.log(`   Particles: ${CONFIG.particles.stars.count + CONFIG.particles.cloudSparkles.count + CONFIG.particles.foregroundSparkles.count}`);
    console.log(`   Reduced motion: ${CONFIG.reducedMotion}`);
    console.log(`   Mobile mode: ${CONFIG.isMobile}`);
  }

  // ============================================
  // Boot
  // ============================================
  
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
