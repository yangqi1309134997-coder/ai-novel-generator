<template>
  <div class="loading-card">
    <div class="loading-card__header" v-if="showHeader">
      <div class="skeleton skeleton--circle" :style="{ width: avatarSize + 'px', height: avatarSize + 'px' }"></div>
      <div class="loading-card__header-text">
        <div class="skeleton skeleton--text" style="width: 40%;"></div>
        <div class="skeleton skeleton--text skeleton--thin" style="width: 28%;"></div>
      </div>
    </div>
    <div class="loading-card__body">
      <div
        v-for="i in rows"
        :key="i"
        class="skeleton skeleton--text"
        :style="{ width: i === rows ? '60%' : '100%' }"
      ></div>
    </div>
    <div class="loading-card__footer" v-if="showFooter">
      <div class="skeleton skeleton--button"></div>
      <div class="skeleton skeleton--button" style="width: 80px;"></div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  rows: {
    type: Number,
    default: 3,
  },
  showHeader: {
    type: Boolean,
    default: true,
  },
  showFooter: {
    type: Boolean,
    default: false,
  },
  avatarSize: {
    type: Number,
    default: 40,
  },
})
</script>

<style scoped>
.loading-card {
  padding: 20px;
  border-radius: 16px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  animation: fadeIn 0.3s ease-out;
}

.loading-card__header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.loading-card__header-text {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.loading-card__body {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.loading-card__footer {
  display: flex;
  gap: 10px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #f1f5f9;
}

/* Skeleton base */
.skeleton {
  border-radius: 6px;
  background: linear-gradient(90deg, #f1f5f9 25%, #e2e8f0 50%, #f1f5f9 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
}

.skeleton--circle {
  border-radius: 50%;
  flex-shrink: 0;
}

.skeleton--text {
  height: 14px;
}

.skeleton--thin {
  height: 10px;
}

.skeleton--button {
  width: 64px;
  height: 32px;
  border-radius: 8px;
}

@keyframes shimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}
</style>
