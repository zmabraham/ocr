import { createRouter, createWebHistory } from 'vue-router'
import UploadView from '../views/UploadView.vue'
import DocumentsView from '../views/DocumentsView.vue'
import ReviewView from '../views/ReviewView.vue'

const routes = [
  {
    path: '/',
    name: 'upload',
    component: UploadView
  },
  {
    path: '/documents',
    name: 'documents',
    component: DocumentsView
  },
  {
    path: '/review/:documentId?',
    name: 'review',
    component: ReviewView,
    props: true
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
