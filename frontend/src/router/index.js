import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { cleanupUploadSessionNoAuth, cleanupPdfSessionNoAuth } from '../utils/uploadSession'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    component: () => import('../views/Layout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        redirect: '/questions'
      },
      {
        path: 'questions',
        name: 'Questions',
        component: () => import('../views/Questions.vue'),
        meta: { title: '题库' }
      },
      {
        path: 'questions/:uuid',
        name: 'PaperDetail',
        component: () => import('../views/PaperDetail.vue'),
        meta: { title: '试卷详情' }
      },
      {
        path: 'questions/create',
        name: 'QuestionCreate',
        component: () => import('../views/QuestionEdit.vue'),
        meta: { title: '添加题目' }
      },
      {
        path: 'import',
        name: 'QuestionImport',
        component: () => import('../views/QuestionAIImport.vue'),
        meta: { title: '批量导入题目' }
      },
      {
        path: 'questions/:id/edit',
        name: 'QuestionEdit',
        component: () => import('../views/QuestionEdit.vue'),
        meta: { title: '编辑题目' }
      },
      {
        path: 'questions/compose',
        name: 'PaperCompose',
        component: () => import('../views/PaperCompose.vue'),
        meta: { title: '新建试卷' }
      },
      {
        path: 'papers',
        name: 'Papers',
        component: () => import('../views/Papers.vue'),
        meta: { title: '试卷列表' }
      },
      {
        path: 'papers/:id/edit',
        name: 'PaperEdit',
        component: () => import('../views/PaperCompose.vue'),
        meta: { title: '编辑试卷' }
      },

      {
        path: 'institutes',
        name: 'Institutes',
        component: () => import('../views/Institutes.vue'),
        meta: { title: '机构管理' }
      },
      {
        path: 'classes',
        name: 'Classes',
        component: () => import('../views/Classes.vue'),
        meta: { title: '班级' }
      },
      {
        path: 'classes/create',
        name: 'ClassCreate',
        component: () => import('../views/ClassCreate.vue'),
        meta: { title: '创建班级', roles: ['admin', 'teacher'] }
      },
      {
        path: 'classes/:id',
        name: 'ClassDetail',
        component: () => import('../views/ClassDetail.vue'),
        meta: { title: '班级详情' }
      },
      {
        path: 'classes/:classId/exams/:examId/scores',
        name: 'PaperScore',
        component: () => import('../views/PaperScore.vue'),
        meta: { title: '成绩登记' }
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('../views/Users.vue'),
        meta: { title: '用户管理', roles: ['admin', 'teacher'] }
      },
      {
        path: 'account-settings',
        name: 'AccountSettings',
        component: () => import('../views/AccountSettings.vue'),
        meta: { title: '账号设置' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  
  // 离开批量导入/单题编辑/试卷创建页面时，清理上传会话和PDF预览会话（作为安全兜底）
  const sessionPages = ['QuestionImport', 'QuestionCreate', 'QuestionEdit', 'PaperCompose', 'PaperEdit']
  if (from.name && sessionPages.includes(from.name) && to.name !== from.name) {
    cleanupUploadSessionNoAuth()
    cleanupPdfSessionNoAuth()
  }
  
  if (to.meta.requiresAuth !== false && !authStore.isLoggedIn) {
    next('/login')
  } else if (to.path === '/login' && authStore.isLoggedIn) {
    next('/')
  } else {
    next()
  }
})

export default router
