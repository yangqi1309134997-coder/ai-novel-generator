<template>
  <div class="auth-layout">
    <!-- Floating decorative circles -->
    <div class="auth-decor">
      <div class="auth-decor__circle auth-decor__circle--1"></div>
      <div class="auth-decor__circle auth-decor__circle--2"></div>
      <div class="auth-decor__circle auth-decor__circle--3"></div>
      <div class="auth-decor__circle auth-decor__circle--4"></div>
    </div>

    <!-- Content -->
    <div class="auth-content">
      <div class="auth-card">
        <div class="auth-card__header">
          <div class="auth-brand">
            <div class="auth-brand__mark">AI</div>
            <span class="auth-brand__text">AI Novel Generator</span>
          </div>
        </div>
        <div class="auth-card__body">
          <router-view />
        </div>
      </div>

      <footer class="auth-footer">
        <p>&copy; 2026 新疆幻城网安科技有限责任公司</p>
        <p>AI Novel Generator Web v5.0</p>
      </footer>
    </div>
  </div>
</template>

<script setup>
</script>

<style scoped>
.auth-layout {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #a78bfa 100%);
  position: relative;
  overflow: hidden;
}

/* Floating decorative circles */
.auth-decor {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
}

.auth-decor__circle {
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.08);
}

.auth-decor__circle--1 {
  width: 400px;
  height: 400px;
  top: -100px;
  right: -80px;
  animation: float 8s ease-in-out infinite;
}

.auth-decor__circle--2 {
  width: 250px;
  height: 250px;
  bottom: -60px;
  left: -40px;
  animation: float 10s ease-in-out infinite reverse;
}

.auth-decor__circle--3 {
  width: 120px;
  height: 120px;
  top: 30%;
  left: 10%;
  background: rgba(255, 255, 255, 0.05);
  animation: float 6s ease-in-out infinite 1s;
}

.auth-decor__circle--4 {
  width: 180px;
  height: 180px;
  bottom: 20%;
  right: 15%;
  background: rgba(255, 255, 255, 0.06);
  animation: float 9s ease-in-out infinite 2s;
}

@keyframes float {
  0%, 100% {
    transform: translateY(0) scale(1);
  }
  50% {
    transform: translateY(-20px) scale(1.05);
  }
}

/* Content area */
.auth-content {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
  max-width: 480px;
  padding: 24px;
}

/* Card */
.auth-card {
  width: 100%;
  background: #ffffff;
  border-radius: 20px;
  box-shadow:
    0 24px 48px rgba(0, 0, 0, 0.15),
    0 8px 16px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  animation: slideUp 0.5s ease-out;
}

.auth-card__header {
  padding: 32px 32px 0;
}

.auth-brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.auth-brand__mark {
  width: 44px;
  height: 44px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff;
  font-weight: 800;
  font-size: 16px;
  letter-spacing: 0.04em;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
}

.auth-brand__text {
  font-size: 18px;
  font-weight: 700;
  color: #1e293b;
}

.auth-card__body {
  padding: 24px 32px 32px;
}

/* Footer */
.auth-footer {
  margin-top: 24px;
  text-align: center;
  color: rgba(255, 255, 255, 0.7);
  font-size: 13px;
  line-height: 1.8;
}

.auth-footer p {
  margin: 0;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(24px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Responsive */
@media (max-width: 520px) {
  .auth-content {
    padding: 16px;
  }

  .auth-card__header {
    padding: 24px 20px 0;
  }

  .auth-card__body {
    padding: 20px;
  }
}
</style>
