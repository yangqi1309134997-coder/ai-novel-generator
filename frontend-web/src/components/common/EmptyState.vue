<template>
  <div class="empty-state">
    <div class="empty-state__illustration">
      <svg
        width="120"
        height="120"
        viewBox="0 0 120 120"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <!-- Background circle -->
        <circle cx="60" cy="60" r="56" fill="#f1f5f9" />
        <!-- Document / box shape -->
        <rect x="36" y="30" width="48" height="56" rx="6" fill="#e2e8f0" />
        <rect x="36" y="30" width="48" height="56" rx="6" stroke="#cbd5e1" stroke-width="1.5" />
        <!-- Lines on document -->
        <line x1="46" y1="46" x2="74" y2="46" stroke="#cbd5e1" stroke-width="2" stroke-linecap="round" />
        <line x1="46" y1="56" x2="68" y2="56" stroke="#cbd5e1" stroke-width="2" stroke-linecap="round" />
        <line x1="46" y1="66" x2="62" y2="66" stroke="#cbd5e1" stroke-width="2" stroke-linecap="round" />
        <!-- Decorative dots -->
        <circle cx="84" cy="78" r="10" fill="#e0e7ff" />
        <circle cx="84" cy="78" r="10" stroke="#c7d2fe" stroke-width="1" />
        <path d="M81 78L83.5 80.5L88 76" stroke="#818cf8" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
        <!-- Small star / spark -->
        <path d="M30 38L32 34L34 38L38 40L34 42L32 46L30 42L26 40Z" fill="#c7d2fe" />
      </svg>
    </div>
    <div class="empty-state__text">
      <h3 v-if="title" class="empty-state__title">{{ title }}</h3>
      <p v-if="description" class="empty-state__desc">{{ description }}</p>
    </div>
    <div v-if="$slots.actions" class="empty-state__actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    default: '暂无数据',
  },
  description: {
    type: String,
    default: '',
  },
})
</script>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  text-align: center;
}

.empty-state__illustration {
  margin-bottom: 20px;
  animation: fadeIn 0.5s ease-out;
}

.empty-state__title {
  margin: 0 0 8px;
  font-size: 16px;
  font-weight: 600;
  color: #475569;
}

.empty-state__desc {
  margin: 0;
  font-size: 14px;
  color: #94a3b8;
  max-width: 320px;
  line-height: 1.6;
}

.empty-state__actions {
  margin-top: 20px;
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: center;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
