<template>
  <div class="page-header">
    <div class="page-header__main">
      <h1 class="page-header__title">{{ title }}</h1>
      <p v-if="description" class="page-header__desc">{{ description }}</p>
    </div>
    <div v-if="$slots.actions" class="page-header__actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    required: true,
  },
  description: {
    type: String,
    default: '',
  },
})
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}

.page-header__main {
  flex: 1;
  min-width: 0;
}

.page-header__title {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
  color: #1e293b;
  line-height: 1.3;
}

.page-header__desc {
  margin: 6px 0 0;
  font-size: 14px;
  color: #64748b;
  line-height: 1.6;
}

.page-header__actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
  flex-wrap: wrap;
}

@media (max-width: 640px) {
  .page-header {
    flex-direction: column;
  }
}
</style>
