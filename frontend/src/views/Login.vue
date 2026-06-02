<template>
  <div class="login-container">
    <el-card class="login-card">
      <template #header>
        <h2>物理竞赛题库管理系统</h2>
      </template>
      
      <el-form :model="form" :rules="rules" ref="formRef" label-position="left" label-width="0" hide-required-asterisk>
        <el-form-item prop="username" class="login-form-item">
          <span class="form-label">账号</span>
          <el-input v-model="form.username" placeholder="请输入账号" class="form-input" />
        </el-form-item>
        
        <el-form-item prop="password" class="login-form-item">
          <span class="form-label">密码</span>
          <el-input 
            v-model="form.password" 
            type="password" 
            placeholder="请输入密码"
            show-password
            @keyup.enter="handleLogin"
            class="form-input"
          />
        </el-form-item>
        
        <el-form-item class="login-form-item">
          <span class="form-label"></span>
          <el-button type="primary" @click="handleLogin" :loading="loading" class="form-input">
            登 录
          </el-button>
        </el-form-item>
      </el-form>
      <div class="login-hint">
        新账户的初始密码与账号相同<br>
        教师账号前四位为 1906<br>
        学生账号前四位为 1026
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const formRef = ref()
const loading = ref(false)

const form = reactive({
  username: '',
  password: ''
})

const rules = {
  username: [{ message: '请输入账号', trigger: 'blur' }],
  password: [{ message: '请输入密码', trigger: 'blur' }]
}

async function handleLogin() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    await authStore.login(form.username, form.password)
    ElMessage.success('登录成功')
    router.push('/')
  } catch (error) {
    // 登录失败：清空密码，提示错误
    form.password = ''
    ElMessage.error('用户名或密码错误')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  width: 400px;
}

.login-card h2 {
  text-align: center;
  margin: 0;
  color: #303133;
}

.login-hint {
  text-align: left;
  margin-top: 15px;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 4px;
  font-size: 13px;
  color: #909399;
}

.demo-accounts {
  margin-top: 20px;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 4px;
  font-size: 12px;
  color: #909399;
}

.demo-accounts p {
  margin: 5px 0;
}

.login-form-item :deep(.el-form-item__content) {
  display: flex;
  align-items: center;
}

.form-label {
  width: 50px;
  flex-shrink: 0;
  text-align: left;
}

.form-input {
  flex: 1;
}

.form-input.el-button {
  width: 100%;
  margin-left: 0;
}
</style>
