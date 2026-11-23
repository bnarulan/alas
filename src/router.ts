import { createRouter, createWebHashHistory } from 'vue-router'
import type { usePlatform } from './stores/platform'

export function makeRouter(store: ReturnType<typeof usePlatform>) {
  const router = createRouter({
    history: createWebHashHistory(),
    scrollBehavior: () => ({ top: 0 }),
    routes: [
      { path: '/', name: 'login', component: () => import('./views/LoginView.vue') },
      { path: '/learn', name: 'student', component: () => import('./views/StudentDashboard.vue'), meta: { role: 'student' } },
      { path: '/learn/lessons', name: 'catalog', component: () => import('./views/CatalogView.vue'), meta: { role: 'student' } },
      { path: '/learn/lessons/:id', name: 'lesson', component: () => import('./views/LessonView.vue'), meta: { role: 'student' } },
      { path: '/learn/vocabulary', name: 'vocabulary', component: () => import('./views/VocabularyView.vue'), meta: { role: 'student' } },
      { path: '/learn/homework', name: 'homework', component: () => import('./views/HomeworkView.vue'), meta: { role: 'student' } },
      { path: '/learn/profile', name: 'profile', component: () => import('./views/ProfileView.vue'), meta: { role: 'student' } },
      { path: '/teach', name: 'teacher', component: () => import('./views/TeacherDashboard.vue'), meta: { role: 'teacher' } },
      { path: '/teach/lessons', name: 'manage', component: () => import('./views/ManageLessons.vue'), meta: { role: 'teacher' } },
      { path: '/teach/lessons/edit/:id?', name: 'editor', component: () => import('./views/LessonEditor.vue'), meta: { role: 'teacher' } },
      { path: '/teach/classes', name: 'classes', component: () => import('./views/ClassesView.vue'), meta: { role: 'teacher' } },
      { path: '/teach/results', name: 'results', component: () => import('./views/ResultsView.vue'), meta: { role: 'teacher' } },
      { path: '/:pathMatch(.*)*', redirect: '/' },
    ],
  })
  router.beforeEach(to => {
    if (to.meta.role && store.user?.role !== to.meta.role) {
      return { name: store.user?.role ?? 'login' }
    }
    if (to.name === 'login' && store.user) return { name: store.user.role }
  })
  return router
}
