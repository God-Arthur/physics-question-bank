<template>
  <el-container class="layout-container">
    <el-aside width="220px">
      <div class="logo">
        <el-icon><Notebook /></el-icon>
        <span>物理竞赛题库</span>
      </div>
      
      <el-menu
        :default-active="activeMenu"
        router
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409EFF"
      >
        <el-menu-item index="/questions" v-if="isTeacherOrAdmin">
          <el-icon><Document /></el-icon>
          <span>题库</span>
        </el-menu-item>
        
        <el-menu-item index="/papers" v-if="isTeacherOrAdmin">
          <el-icon><Tickets /></el-icon>
          <span>试卷列表</span>
        </el-menu-item>
        
        <el-menu-item index="/my-exams" v-if="isStudent">
          <el-icon><Tickets /></el-icon>
          <span>我的考试</span>
        </el-menu-item>
        
        <el-menu-item index="/classes">
          <el-icon><School /></el-icon>
          <span>班级</span>
        </el-menu-item>
        
        <el-menu-item index="/users" v-if="isTeacherOrAdmin">
          <el-icon><User /></el-icon>
          <span>用户管理</span>
        </el-menu-item>
        
        <el-menu-item index="/account-settings">
          <el-icon><Setting /></el-icon>
          <span>账户设置</span>
        </el-menu-item>
      </el-menu>
      
      <div class="sidebar-footer">
        <div class="dev-info">
          <div>由 张三 开发</div>
          <div class="email-line">
            <el-icon><Message /></el-icon>
            <span>redaunt06@gmail.com</span>
          </div>
          <div class="version">beta</div>
        </div>
      </div>
    </el-aside>
    
    <el-container>
      <el-header>
        <div class="header-title">{{ pageTitle }}</div>
        <div class="header-user">
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              <el-icon><UserFilled /></el-icon>
              {{ authStore.user?.real_name || authStore.user?.username }}
              <el-tag size="small" style="margin-left: 8px">{{ roleLabel }}</el-tag>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      
      <el-main>
        <router-view :key="$route.fullPath" />
      </el-main>
    </el-container>
    
    <!-- 强制修改密码弹窗 -->
    <el-dialog
      v-model="changePasswordVisible"
      title="修改密码"
      width="400px"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :show-close="false"
    >
      <el-alert type="warning" :closable="false" style="margin-bottom: 15px">
        首次登录请修改默认密码
      </el-alert>
      <el-form :model="pwdForm" :rules="pwdRules" ref="pwdFormRef" label-width="100px" hide-required-asterisk>
        <el-form-item label="新密码" prop="password">
          <el-input v-model="pwdForm.password" type="password" placeholder="请输入新密码（至少6位）" show-password />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirm">
          <el-input v-model="pwdForm.confirm" type="password" placeholder="请再次输入新密码" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button type="primary" @click="handleChangePassword" :loading="pwdSubmitting">确定修改</el-button>
      </template>
    </el-dialog>
  </el-container>
</template>

<script setup>
import { computed, onMounted, ref, reactive, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../utils/api'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const activeMenu = computed(() => {
  const path = route.path
  if (path.startsWith('/questions')) return '/questions'
  if (path.startsWith('/papers')) return '/papers'
  if (path.startsWith('/my-exams')) return '/my-exams'
  if (path.startsWith('/classes')) return '/classes'
  if (path.startsWith('/users')) return '/users'
  return '/questions'
})

const isTeacherOrAdmin = computed(() => ['admin', 'teacher'].includes(authStore.userRole))

const pageTitle = computed(() => route.meta?.title || '首页')

const roleLabel = computed(() => {
  const labels = {
    admin: '管理员',
    teacher: '教师',
    student: '学生'
  }
  return labels[authStore.userRole] || ''
})

function handleCommand(command) {
  if (command === 'logout') {
    authStore.logout()
    router.push('/login')
  }
}

// 强制修改密码
const changePasswordVisible = ref(false)
const pwdSubmitting = ref(false)
const pwdFormRef = ref()
const pwdForm = reactive({ password: '', confirm: '' })
const pwdRules = {
  password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码至少6个字符', trigger: 'blur' }
  ],
  confirm: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== pwdForm.password) callback(new Error('两次输入的密码不一致'))
        else callback()
      },
      trigger: 'blur'
    }
  ]
}

watch(() => authStore.needChangePassword, (val) => {
  if (val) {
    changePasswordVisible.value = true
    pwdForm.password = ''
    pwdForm.confirm = ''
  }
}, { immediate: true })

async function handleChangePassword() {
  const valid = await pwdFormRef.value.validate().catch(() => false)
  if (!valid) return
  pwdSubmitting.value = true
  try {
    await api.put(`/auth/users/${authStore.user.id}`, { password: pwdForm.password })
    ElMessage.success('密码修改成功')
    changePasswordVisible.value = false
    await authStore.fetchUser()
  } catch (error) {
    // 错误已处理
  } finally {
    pwdSubmitting.value = false
  }
}

onMounted(() => {
  authStore.fetchUser()
})
</script>

<style scoped>
.layout-container {
  min-height: 100vh;
}

.el-aside {
  background-color: #304156;
  position: relative;
  display: flex;
  flex-direction: column;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 18px;
  font-weight: bold;
  border-bottom: 1px solid #3a4a5e;
}

.logo .el-icon {
  font-size: 24px;
  margin-right: 8px;
}

.el-menu {
  border-right: none;
  flex: 1;
  overflow-y: auto;
  padding-bottom: 100px;
}

.sidebar-footer {
  position: fixed;
  bottom: 0;
  left: 0;
  width: 220px;
  padding: 15px 20px;
  background-color: #304156;
  border-top: 1px solid #3a4a5e;
  z-index: 100;
}

.dev-info {
  color: #bfcbd9;
  font-size: 12px;
  text-align: center;
}

.dev-info .email-line {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 5px;
  gap: 5px;
}

.dev-info .version {
  margin-top: 5px;
  color: #909399;
  font-size: 11px;
}

.el-header {
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
}

.header-title {
  font-size: 18px;
  font-weight: 500;
}

.user-info {
  display: flex;
  align-items: center;
  cursor: pointer;
}

.el-main {
  background: #f5f7fa;
  padding: 20px;
}
</style>
