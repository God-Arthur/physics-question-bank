<template>
  <div class="account-settings-page">
    <el-card>
      <template #header>
        <span>账户设置</span>
      </template>
      
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px" style="max-width: 500px" hide-required-asterisk>
        <el-form-item label="账号">
          <el-input :model-value="authStore.user?.username" disabled />
        </el-form-item>
        
        <el-form-item label="姓名">
          <el-input :model-value="authStore.user?.real_name || authStore.user?.username" disabled />
        </el-form-item>
        
        <el-form-item label="角色">
          <el-tag :type="roleTag(authStore.userRole)">{{ roleLabel(authStore.userRole) }}</el-tag>
        </el-form-item>
        
        <el-form-item label="当前密码" prop="old_password">
          <el-input v-model="form.old_password" type="password" placeholder="请输入当前密码" show-password />
        </el-form-item>
        
        <el-form-item label="新密码" prop="new_password">
          <el-input v-model="form.new_password" type="password" placeholder="请输入新密码（至少6位）" show-password />
        </el-form-item>
        
        <el-form-item label="确认新密码" prop="confirm_password">
          <el-input v-model="form.confirm_password" type="password" placeholder="请再次输入新密码" show-password />
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" @click="handleSubmit" :loading="submitting">保存修改</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../utils/api'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const formRef = ref()
const submitting = ref(false)

const form = reactive({
  old_password: '',
  new_password: '',
  confirm_password: ''
})

const rules = {
  old_password: [{ required: true, message: '请输入当前密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码至少6个字符', trigger: 'blur' }
  ],
  confirm_password: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== form.new_password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

function roleTag(role) {
  const tags = { admin: 'danger', teacher: 'warning', student: 'success' }
  return tags[role] || ''
}

function roleLabel(role) {
  const labels = { admin: '管理员', teacher: '教师', student: '学生' }
  return labels[role] || role
}

async function handleSubmit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  // 新密码为空时提示无效
  if (!form.new_password || !form.new_password.trim()) {
    ElMessage.warning('请输入新密码以修改密码')
    return
  }

  submitting.value = true
  try {
    // 先验证当前密码
    const checkRes = await api.post('/auth/login', {
      username: authStore.user.username,
      password: form.old_password
    })

    // 更新密码
    const data = { password: form.new_password }

    await api.put(`/auth/users/${authStore.user.id}`, data)
    ElMessage.success('修改成功')

    // 清空密码字段
    form.old_password = ''
    form.new_password = ''
    form.confirm_password = ''

    // 刷新用户信息
    await authStore.fetchUser()
  } catch (error) {
    if (error?.response?.status === 401) {
      ElMessage.error('当前密码错误')
    }
    // 其他错误已处理
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  // 初始化
})
</script>

<style scoped>
.account-settings-page {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}
</style>
