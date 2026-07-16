import { createRouter, createWebHistory } from 'vue-router'

export default createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: () => import('@/views/DashboardView.vue'),
      meta: { title: '实验总览' },
    },
    {
      path: '/detect',
      name: 'detect',
      component: () => import('@/views/DetectionView.vue'),
      meta: { title: '单图检测' },
    },
    {
      path: '/evaluate',
      name: 'evaluate',
      component: () => import('@/views/EvaluationView.vue'),
      meta: { title: '验证集评估' },
    },
    {
      path: '/analysis',
      name: 'analysis',
      component: () => import('@/views/AnalysisView.vue'),
      meta: { title: '错误归因' },
    },
  ],
})
