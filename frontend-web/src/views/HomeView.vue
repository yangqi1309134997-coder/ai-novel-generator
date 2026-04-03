<template>
  <div class="landing">
    <!-- ==================== Navbar ==================== -->
    <header class="landing-navbar">
      <div class="landing-navbar__inner">
        <div class="landing-navbar__brand" @click="scrollToTop">
          <div class="landing-navbar__logo">AI</div>
          <span class="landing-navbar__title">AI Novel Studio</span>
        </div>

        <nav class="landing-navbar__nav hide-tablet">
          <a class="landing-navbar__link" @click.prevent="scrollToSection('features')">产品特点</a>
          <a class="landing-navbar__link" @click.prevent="scrollToSection('pricing')">定价方案</a>
          <a class="landing-navbar__link" @click.prevent="scrollToSection('workflow')">工作流程</a>
        </nav>

        <div class="landing-navbar__actions">
          <n-button
            v-if="authStore.isAuthenticated"
            type="primary"
            @click="router.push({ name: 'Workspace' })"
          >
            进入工作台
          </n-button>
          <template v-else>
            <n-button quaternary @click="router.push({ name: 'Login' })">登录</n-button>
            <n-button type="primary" @click="router.push({ name: 'Login' })">免费开始</n-button>
          </template>
        </div>
      </div>
    </header>

    <!-- ==================== Hero ==================== -->
    <section class="landing-hero">
      <div class="landing-hero__glow"></div>
      <div class="landing-hero__inner">
        <div class="landing-hero__badge">Snowflake Writing Method</div>
        <h1 class="landing-hero__title">
          用
          <n-gradient-text type="info" :size="48" style="font-size: inherit; line-height: inherit;">
            AI
          </n-gradient-text>
          写出真正好看的网络小说
        </h1>
        <p class="landing-hero__subtitle">
          雪花写作法驱动，支持 8 种文学风格，一键完成大纲规划到整本生成
        </p>
        <div class="landing-hero__actions">
          <n-button type="primary" size="large" @click="handleCta">
            开始创作
            <template #icon>
              <n-icon><arrow-forward-outline /></n-icon>
            </template>
          </n-button>
          <n-button size="large" quaternary @click="scrollToSection('features')">
            了解更多
          </n-button>
        </div>
        <div class="landing-hero__stats">
          <div class="landing-hero__stat">
            <span class="landing-hero__stat-value">8</span>
            <span class="landing-hero__stat-label">文学风格</span>
          </div>
          <div class="landing-hero__stat-divider"></div>
          <div class="landing-hero__stat">
            <span class="landing-hero__stat-value">200+</span>
            <span class="landing-hero__stat-label">章 / 项目</span>
          </div>
          <div class="landing-hero__stat-divider"></div>
          <div class="landing-hero__stat">
            <span class="landing-hero__stat-value">5+</span>
            <span class="landing-hero__stat-label">导出格式</span>
          </div>
        </div>
      </div>
    </section>

    <!-- ==================== Features ==================== -->
    <section id="features" class="landing-section">
      <div class="landing-section__inner">
        <div class="landing-section__header">
          <h2 class="landing-section__title">为什么选择 AI Novel Studio</h2>
          <p class="landing-section__subtitle">专为网络小说创作者设计的全流程 AI 写作工具</p>
        </div>

        <div class="landing-features">
          <div
            v-for="feature in features"
            :key="feature.title"
            class="landing-feature-card"
          >
            <div class="landing-feature-card__icon" v-html="feature.icon"></div>
            <h3 class="landing-feature-card__title">{{ feature.title }}</h3>
            <p class="landing-feature-card__desc">{{ feature.desc }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- ==================== Workflow ==================== -->
    <section id="workflow" class="landing-section landing-section--gray">
      <div class="landing-section__inner">
        <div class="landing-section__header">
          <h2 class="landing-section__title">四步完成创作</h2>
          <p class="landing-section__subtitle">从灵感到成书，只需几个简单步骤</p>
        </div>

        <div class="landing-workflow">
          <div
            v-for="(step, index) in workflowSteps"
            :key="step.title"
            class="landing-workflow__step"
          >
            <div class="landing-workflow__number">{{ index + 1 }}</div>
            <div class="landing-workflow__icon" v-html="step.icon"></div>
            <h4 class="landing-workflow__title">{{ step.title }}</h4>
            <p class="landing-workflow__desc">{{ step.desc }}</p>
            <div v-if="index < workflowSteps.length - 1" class="landing-workflow__arrow hide-mobile">
              <svg width="32" height="16" viewBox="0 0 32 16" fill="none">
                <path d="M0 8H28M28 8L22 2M28 8L22 14" stroke="#6366f1" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ==================== Pricing ==================== -->
    <section id="pricing" class="landing-section">
      <div class="landing-section__inner">
        <div class="landing-section__header">
          <h2 class="landing-section__title">选择适合你的方案</h2>
          <p class="landing-section__subtitle">从免费开始，随时升级</p>
        </div>

        <div class="landing-pricing">
          <div
            v-for="plan in pricingPlans"
            :key="plan.name"
            class="landing-pricing-card"
            :class="{ 'landing-pricing-card--featured': plan.featured }"
          >
            <div v-if="plan.featured" class="landing-pricing-card__badge">推荐</div>
            <h3 class="landing-pricing-card__name">{{ plan.name }}</h3>
            <div class="landing-pricing-card__price">
              <template v-if="plan.price === 0">
                免费
              </template>
              <template v-else>
                <span class="landing-pricing-card__currency">&yen;</span>{{ plan.price }}
                <span class="landing-pricing-card__period">/月</span>
              </template>
            </div>
            <p class="landing-pricing-card__desc">{{ plan.desc }}</p>
            <ul class="landing-pricing-card__features">
              <li v-for="f in plan.features" :key="f">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none" style="flex-shrink:0;margin-top:2px;">
                  <path d="M3.5 8.5L6.5 11.5L12.5 4.5" stroke="#6366f1" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                {{ f }}
              </li>
            </ul>
            <n-button
              :type="plan.featured ? 'primary' : 'default'"
              block
              size="large"
              @click="handlePlanCta(plan)"
            >
              {{ plan.cta }}
            </n-button>
          </div>
        </div>
      </div>
    </section>

    <!-- ==================== CTA ==================== -->
    <section class="landing-cta">
      <div class="landing-cta__inner">
        <h2 class="landing-cta__title">开始你的 AI 创作之旅</h2>
        <p class="landing-cta__subtitle">注册即送免费额度，无需信用卡</p>
        <n-button
          type="primary"
          size="large"
          ghost
          style="color:#fff;--n-color-hover:rgba(255,255,255,0.15);--n-border-hover:1px solid rgba(255,255,255,0.4);--n-text-color:#fff;--n-text-color-hover:#fff;"
          @click="router.push({ name: 'Login' })"
        >
          免费注册
        </n-button>
      </div>
    </section>

    <!-- ==================== Footer ==================== -->
    <footer class="landing-footer">
      <div class="landing-footer__inner">
        <div class="landing-footer__grid">
          <div class="landing-footer__col">
            <div class="landing-footer__brand">
              <div class="landing-footer__logo">AI</div>
              <span>AI Novel Studio</span>
            </div>
            <p class="landing-footer__about">
              用 AI 赋能创作，让每个人都能写出精彩的网络小说。
            </p>
          </div>

          <div class="landing-footer__col">
            <h4 class="landing-footer__heading">产品</h4>
            <a class="landing-footer__link" @click.prevent="scrollToSection('features')">功能介绍</a>
            <a class="landing-footer__link" @click.prevent="scrollToSection('pricing')">定价方案</a>
            <a class="landing-footer__link" @click.prevent="scrollToSection('workflow')">工作流程</a>
          </div>

          <div class="landing-footer__col">
            <h4 class="landing-footer__heading">支持</h4>
            <a class="landing-footer__link" href="javascript:void(0)">帮助中心</a>
            <a class="landing-footer__link" href="javascript:void(0)">API 文档</a>
            <a class="landing-footer__link" href="javascript:void(0)">联系我们</a>
          </div>

          <div class="landing-footer__col">
            <h4 class="landing-footer__heading">法律</h4>
            <a class="landing-footer__link" href="javascript:void(0)">用户协议</a>
            <a class="landing-footer__link" href="javascript:void(0)">隐私政策</a>
            <a class="landing-footer__link" href="javascript:void(0)">Cookie 政策</a>
          </div>
        </div>

        <div class="landing-footer__bottom">
          <p>&copy; 2026 新疆幻城网安科技有限责任公司 &middot; AI Novel Studio v6.0</p>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { NButton, NGradientText, NIcon, useMessage } from 'naive-ui'
import { ArrowForwardOutline } from '@vicons/ionicons5'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const message = useMessage()
const authStore = useAuthStore()

/* ---- data ---- */
const features = [
  {
    icon: '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>',
    title: '雪花写作法',
    desc: '从一句话梗概出发，层层递进完成角色设定、章节蓝图和正文生成，确保故事结构严谨。',
  },
  {
    icon: '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/><line x1="9" y1="9" x2="9.01" y2="9"/><line x1="15" y1="9" x2="15.01" y2="9"/></svg>',
    title: '8 种文学风格',
    desc: '热血爽文、悬疑推理、言情甜宠、仙侠修真、都市生活等风格一键切换，精准匹配目标读者。',
  },
  {
    icon: '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>',
    title: '一键整本生成',
    desc: '设定完成后一键启动整本生成，后台自动完成大纲到章节的逐章写作，支持 TXT/MD/DOCX 等多格式导出。',
  },
]

const workflowSteps = [
  {
    icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>',
    title: '输入设定',
    desc: '填写书名、类型、角色信息和故事梗概',
  },
  {
    icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>',
    title: '选择风格',
    desc: '从 8 种文学风格中选择最适合的风格',
  },
  {
    icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>',
    title: '一键生成',
    desc: 'AI 按雪花写作法自动生成大纲和正文',
  },
  {
    icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>',
    title: '阅读 / 导出',
    desc: '在线阅读、润色续写，或导出为多种格式',
  },
]

const pricingPlans = [
  {
    name: '免费版',
    price: 0,
    desc: '适合初次体验 AI 创作',
    features: ['每天 3 章生成额度', '3 个项目上限', '雪花写作法', 'TXT 导出', '基础润色工具'],
    cta: '免费开始',
    featured: false,
  },
  {
    name: '基础版',
    price: 29,
    desc: '适合日常更新的网文作者',
    features: ['每天 50 章生成额度', '无限项目', '8 种文学风格', '全格式导出', '高级润色 + 续写', '后台批量生成'],
    cta: '立即订阅',
    featured: true,
  },
  {
    name: '高级版',
    price: 99,
    desc: '适合专业创作团队和工作室',
    features: ['无限章节生成', '无限项目', '8 种文学风格', '全格式导出', '高级润色 + 续写', '后台批量生成', '优先队列', '专属客服支持'],
    cta: '立即订阅',
    featured: false,
  },
]

/* ---- methods ---- */
function scrollToTop() {
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function scrollToSection(id) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function handleCta() {
  if (authStore.isAuthenticated) {
    router.push({ name: 'Workspace' })
  } else {
    router.push({ name: 'Login' })
  }
}

function handlePlanCta(plan) {
  if (authStore.isAuthenticated) {
    router.push({ name: 'Account' })
  } else {
    router.push({ name: 'Login' })
  }
}
</script>

<style scoped>
/* ============================================
   Landing page — full self-contained styles
   ============================================ */

.landing {
  --lp-purple: #6366f1;
  --lp-purple-light: #8b5cf6;
  --lp-purple-bg: rgba(99, 102, 241, 0.06);
  --lp-gray-50: #f8fafc;
  --lp-gray-100: #f1f5f9;
  --lp-gray-200: #e2e8f0;
  --lp-gray-400: #94a3b8;
  --lp-gray-500: #64748b;
  --lp-gray-600: #475569;
  --lp-gray-800: #1e293b;
  --lp-gray-900: #0f172a;
  --lp-max-w: 1200px;

  font-family: 'Inter', 'Noto Sans SC', system-ui, -apple-system, sans-serif;
  color: var(--lp-gray-800);
  background: #fff;
  overflow-x: hidden;
}

/* ---- Navbar ---- */
.landing-navbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-bottom: 1px solid var(--lp-gray-200);
  transition: box-shadow 0.3s ease;
}

.landing-navbar:hover {
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06);
}

.landing-navbar__inner {
  max-width: var(--lp-max-w);
  margin: 0 auto;
  padding: 0 32px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}

.landing-navbar__brand {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  user-select: none;
}

.landing-navbar__logo {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  border-radius: 10px;
  background: linear-gradient(135deg, var(--lp-purple), var(--lp-purple-light));
  color: #fff;
  font-weight: 800;
  font-size: 13px;
  letter-spacing: 0.02em;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
}

.landing-navbar__title {
  font-size: 17px;
  font-weight: 700;
  color: var(--lp-gray-900);
}

.landing-navbar__nav {
  display: flex;
  gap: 8px;
}

.landing-navbar__link {
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  color: var(--lp-gray-600);
  cursor: pointer;
  transition: all 0.2s ease;
}

.landing-navbar__link:hover {
  color: var(--lp-purple);
  background: var(--lp-purple-bg);
}

.landing-navbar__actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* ---- Hero ---- */
.landing-hero {
  position: relative;
  padding: 140px 32px 80px;
  text-align: center;
  overflow: hidden;
}

.landing-hero__glow {
  position: absolute;
  top: -120px;
  left: 50%;
  transform: translateX(-50%);
  width: 800px;
  height: 500px;
  background: radial-gradient(
    ellipse 60% 50% at 50% 0%,
    rgba(99, 102, 241, 0.12) 0%,
    rgba(139, 92, 246, 0.06) 40%,
    transparent 70%
  );
  pointer-events: none;
}

.landing-hero__inner {
  position: relative;
  z-index: 1;
  max-width: 780px;
  margin: 0 auto;
}

.landing-hero__badge {
  display: inline-block;
  padding: 6px 16px;
  border-radius: 999px;
  background: var(--lp-purple-bg);
  color: var(--lp-purple);
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.04em;
  margin-bottom: 24px;
}

.landing-hero__title {
  margin: 0;
  font-size: clamp(2rem, 5vw, 3.2rem);
  font-weight: 800;
  line-height: 1.2;
  color: var(--lp-gray-900);
  letter-spacing: -0.01em;
}

.landing-hero__subtitle {
  margin: 20px auto 0;
  max-width: 540px;
  font-size: 18px;
  line-height: 1.7;
  color: var(--lp-gray-500);
}

.landing-hero__actions {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-top: 36px;
  flex-wrap: wrap;
}

.landing-hero__stats {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 32px;
  margin-top: 56px;
  flex-wrap: wrap;
}

.landing-hero__stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.landing-hero__stat-value {
  font-size: 28px;
  font-weight: 800;
  background: linear-gradient(135deg, var(--lp-purple), var(--lp-purple-light));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.landing-hero__stat-label {
  font-size: 13px;
  color: var(--lp-gray-400);
  font-weight: 500;
}

.landing-hero__stat-divider {
  width: 1px;
  height: 36px;
  background: var(--lp-gray-200);
}

/* ---- Section common ---- */
.landing-section {
  padding: 80px 32px;
}

.landing-section--gray {
  background: var(--lp-gray-50);
}

.landing-section__inner {
  max-width: var(--lp-max-w);
  margin: 0 auto;
}

.landing-section__header {
  text-align: center;
  margin-bottom: 48px;
}

.landing-section__title {
  margin: 0;
  font-size: 32px;
  font-weight: 800;
  color: var(--lp-gray-900);
}

.landing-section__subtitle {
  margin: 12px 0 0;
  font-size: 16px;
  color: var(--lp-gray-500);
}

/* ---- Features ---- */
.landing-features {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
}

.landing-feature-card {
  padding: 32px 28px;
  border-radius: 20px;
  background: #fff;
  border: 1px solid var(--lp-gray-200);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
  transition: transform 0.25s ease, box-shadow 0.25s ease;
}

.landing-feature-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 40px rgba(99, 102, 241, 0.12);
}

.landing-feature-card__icon {
  width: 56px;
  height: 56px;
  display: grid;
  place-items: center;
  border-radius: 16px;
  background: var(--lp-purple-bg);
  margin-bottom: 20px;
}

.landing-feature-card__title {
  margin: 0 0 12px;
  font-size: 18px;
  font-weight: 700;
  color: var(--lp-gray-900);
}

.landing-feature-card__desc {
  margin: 0;
  font-size: 14px;
  line-height: 1.7;
  color: var(--lp-gray-500);
}

/* ---- Workflow ---- */
.landing-workflow {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  align-items: start;
}

.landing-workflow__step {
  position: relative;
  text-align: center;
  padding: 28px 20px;
}

.landing-workflow__number {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  margin: 0 auto 16px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--lp-purple), var(--lp-purple-light));
  color: #fff;
  font-size: 14px;
  font-weight: 700;
}

.landing-workflow__icon {
  margin: 0 auto 16px;
  width: 48px;
  height: 48px;
  display: grid;
  place-items: center;
}

.landing-workflow__title {
  margin: 0 0 8px;
  font-size: 16px;
  font-weight: 700;
  color: var(--lp-gray-900);
}

.landing-workflow__desc {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: var(--lp-gray-500);
}

.landing-workflow__arrow {
  position: absolute;
  right: -20px;
  top: 90px;
}

/* ---- Pricing ---- */
.landing-pricing {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
  align-items: start;
}

.landing-pricing-card {
  position: relative;
  padding: 36px 28px;
  border-radius: 20px;
  background: #fff;
  border: 1px solid var(--lp-gray-200);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
  transition: transform 0.25s ease, box-shadow 0.25s ease;
}

.landing-pricing-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 40px rgba(99, 102, 241, 0.12);
}

.landing-pricing-card--featured {
  border-color: var(--lp-purple);
  border-width: 2px;
  box-shadow: 0 8px 32px rgba(99, 102, 241, 0.15);
}

.landing-pricing-card--featured:hover {
  box-shadow: 0 16px 48px rgba(99, 102, 241, 0.22);
}

.landing-pricing-card__badge {
  position: absolute;
  top: -12px;
  left: 50%;
  transform: translateX(-50%);
  padding: 4px 16px;
  border-radius: 999px;
  background: linear-gradient(135deg, var(--lp-purple), var(--lp-purple-light));
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.04em;
}

.landing-pricing-card__name {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: var(--lp-gray-900);
}

.landing-pricing-card__price {
  margin: 16px 0 0;
  font-size: 40px;
  font-weight: 800;
  color: var(--lp-gray-900);
}

.landing-pricing-card__currency {
  font-size: 22px;
  vertical-align: top;
  line-height: 2;
}

.landing-pricing-card__period {
  font-size: 14px;
  font-weight: 500;
  color: var(--lp-gray-400);
}

.landing-pricing-card__desc {
  margin: 8px 0 0;
  font-size: 14px;
  color: var(--lp-gray-500);
}

.landing-pricing-card__features {
  list-style: none;
  padding: 0;
  margin: 24px 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.landing-pricing-card__features li {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 14px;
  color: var(--lp-gray-600);
  line-height: 1.5;
}

/* ---- CTA ---- */
.landing-cta {
  padding: 80px 32px;
  background: linear-gradient(135deg, var(--lp-purple) 0%, var(--lp-purple-light) 100%);
  text-align: center;
}

.landing-cta__inner {
  max-width: 600px;
  margin: 0 auto;
}

.landing-cta__title {
  margin: 0;
  font-size: clamp(1.8rem, 4vw, 2.4rem);
  font-weight: 800;
  color: #fff;
}

.landing-cta__subtitle {
  margin: 16px 0 0;
  font-size: 16px;
  color: rgba(255, 255, 255, 0.8);
}

.landing-cta .n-button {
  margin-top: 32px;
  min-width: 180px;
}

/* ---- Footer ---- */
.landing-footer {
  background: var(--lp-gray-900);
  color: var(--lp-gray-400);
  padding: 56px 32px 0;
}

.landing-footer__inner {
  max-width: var(--lp-max-w);
  margin: 0 auto;
}

.landing-footer__grid {
  display: grid;
  grid-template-columns: 1.4fr 1fr 1fr 1fr;
  gap: 40px;
}

.landing-footer__brand {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  color: #fff;
  font-size: 16px;
  font-weight: 700;
}

.landing-footer__logo {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  background: linear-gradient(135deg, var(--lp-purple), var(--lp-purple-light));
  color: #fff;
  font-weight: 800;
  font-size: 11px;
}

.landing-footer__about {
  margin: 0;
  font-size: 14px;
  line-height: 1.7;
  color: var(--lp-gray-400);
}

.landing-footer__heading {
  margin: 0 0 16px;
  font-size: 14px;
  font-weight: 600;
  color: #fff;
}

.landing-footer__link {
  display: block;
  padding: 4px 0;
  font-size: 14px;
  color: var(--lp-gray-400);
  cursor: pointer;
  transition: color 0.2s ease;
}

.landing-footer__link:hover {
  color: #fff;
}

.landing-footer__bottom {
  margin-top: 40px;
  padding: 20px 0;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  text-align: center;
  font-size: 13px;
}

.landing-footer__bottom p {
  margin: 0;
}

/* ---- Responsive ---- */
@media (max-width: 1024px) {
  .landing-features {
    grid-template-columns: 1fr 1fr;
  }

  .landing-workflow {
    grid-template-columns: 1fr 1fr;
    gap: 24px;
  }

  .landing-pricing {
    grid-template-columns: 1fr;
    max-width: 440px;
    margin: 0 auto;
  }

  .landing-footer__grid {
    grid-template-columns: 1fr 1fr;
    gap: 32px;
  }
}

@media (max-width: 768px) {
  .landing-navbar__inner {
    padding: 0 16px;
  }

  .landing-hero {
    padding: 120px 16px 60px;
  }

  .landing-section {
    padding: 56px 16px;
  }

  .landing-features {
    grid-template-columns: 1fr;
  }

  .landing-workflow {
    grid-template-columns: 1fr;
  }

  .landing-workflow__arrow {
    display: none;
  }

  .landing-footer__grid {
    grid-template-columns: 1fr;
    gap: 24px;
  }
}
</style>
