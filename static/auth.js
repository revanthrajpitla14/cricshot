/* auth.js — Shared helper: animated particle canvas for auth pages */
(function () {
  const canvas = document.getElementById('auth-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  let W, H, particles = [];

  function resize() {
    W = canvas.width  = window.innerWidth;
    H = canvas.height = window.innerHeight;
  }
  window.addEventListener('resize', resize);
  resize();

  function rand(min, max) { return Math.random() * (max - min) + min; }

  class Particle {
    constructor() { this.reset(); }
    reset() {
      this.x  = rand(0, W);
      this.y  = rand(0, H);
      this.r  = rand(0.8, 2.5);
      this.vx = rand(-0.3, 0.3);
      this.vy = rand(-0.5, -0.1);
      this.alpha = rand(0.2, 0.65);
      this.color = Math.random() > 0.6 ? '#00e88a' : '#00c8ff';
    }
    update() {
      this.x += this.vx;
      this.y += this.vy;
      this.alpha -= 0.0012;
      if (this.alpha <= 0 || this.y < -5) this.reset();
    }
    draw() {
      ctx.globalAlpha = this.alpha;
      ctx.fillStyle   = this.color;
      ctx.shadowBlur  = 8;
      ctx.shadowColor = this.color;
      ctx.beginPath();
      ctx.arc(this.x, this.y, this.r, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  for (let i = 0; i < 80; i++) particles.push(new Particle());

  (function loop() {
    ctx.clearRect(0, 0, W, H);
    ctx.shadowBlur = 0;
    particles.forEach(p => { p.update(); p.draw(); });
    ctx.globalAlpha = 1;
    requestAnimationFrame(loop);
  })();
})();
