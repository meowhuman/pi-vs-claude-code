# Cinematic Sparkle - Twilight Experience

A stunning cinematic scrolling experience featuring parallax layers, glassmorphism cards, and iridescent sparkle particles.

## 📁 Files

- `index.html` - Semantic HTML structure with parallax layers and content sections
- `styles.css` - Complete styling with CSS variables, keyframe animations, and responsive design
- `script.js` - Vanilla JavaScript for parallax, particle generation, and intersection observers

## ✨ Features

### Visual Design
- **Twilight color palette** - Deep navy gradients with iridescent sparkle accents
- **Glassmorphism cards** - Frosted glass effect with subtle glows and backdrop blur
- **3-layer parallax system** - Background stars, floating cloud cluster, and rolling glitter hills
- **200+ dynamic particles** - Stars and sparkles with randomized colors, sizes, and animations

### Animations
- **Twinkle effect** - Particles fade in/out with scale and blur changes
- **Cloud float** - Subtle up/down floating motion (9-13s duration)
- **Parallax scrolling** - Each layer moves at different speeds (0.15x - 0.55x)
- **Glass reveal** - Cards fade up when entering viewport via IntersectionObserver

### Performance Optimizations
- `requestAnimationFrame` for smooth parallax updates
- `translate3d()` for GPU-accelerated transforms
- Passive scroll event listeners
- Reduced particle count on mobile (~45% fewer)
- `will-change` hints for compositing
- `prefers-reduced-motion` support

### Responsive Design
- **Desktop (≥1024px)** - Full 3-layer effect with deep parallax
- **Tablet (768-1023px)** - Slightly reduced effects, 2-column feature grid
- **Mobile (<768px)** - Simplified cloud, full-width cards, tighter blur

## 🎨 Color Palette

### Twilight Backgrounds
- `#0A1628` - Deep navy top
- `#1A2A4A` - Mid twilight
- `#2A3A5A` - Horizon blue
- `#070F1D` - Depth shadow

### Iridescent Sparkles
- `#FFFFFF` - White
- `#FFD700` - Gold
- `#00FFFF` - Cyan
- `#FF69B4` - Pink
- `#9370DB` - Purple

## 🚀 Usage

Open `index.html` in a modern browser. No build process or dependencies required.

## 📝 Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers (iOS Safari, Chrome Mobile)

## 🔧 Customization

Edit the CSS custom properties in `:root` to adjust:
- Color palette
- Parallax speed factors
- Animation durations
- Particle counts (in `CONFIG` object in script.js)

## 📄 License

Free to use and modify.
