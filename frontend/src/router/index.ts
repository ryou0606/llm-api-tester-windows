import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'ModelList',
      component: () => import('@/views/ModelList.vue'),
    },
    {
      path: '/test/:id',
      name: 'ModelTest',
      component: () => import('@/views/ModelTest.vue'),
    },
    {
      path: '/arena',
      name: 'Arena',
      component: () => import('@/views/Arena.vue'),
    },
    {
      path: '/vision',
      name: 'Vision',
      component: () => import('@/views/Vision.vue'),
    },
    {
      path: '/audio',
      name: 'Audio',
      component: () => import('@/views/Audio.vue'),
    },
    {
      path: '/relay',
      name: 'Relay',
      component: () => import('@/views/Relay.vue'),
    },
  ],
})

export default router
