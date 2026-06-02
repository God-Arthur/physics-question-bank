<template>
  <div class="users-page">
    <!-- 管理员 -->
    <el-card v-if="authStore.userRole === 'admin'" style="margin-bottom: 20px">
      <template #header>
        <div class="card-header">
          <span><el-tag type="danger" style="margin-right: 8px">管理员</el-tag></span>
        </div>
      </template>
      <el-table :data="adminUsers" v-loading="loading" stripe>
        <el-table-column prop="username" label="账号" width="150" />
        <el-table-column label="姓名" width="150">
          <template #default="{ row }">
            {{ row.real_name || row.username }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 教师 -->
    <el-card v-if="authStore.userRole === 'admin'" style="margin-bottom: 20px">
      <template #header>
        <div class="card-header">
          <span><el-tag type="warning" style="margin-right: 8px">教师</el-tag></span>
          <div>
            <el-button type="primary" size="small" @click="showAddDialog('teacher')">
              <el-icon><Plus /></el-icon>
              添加教师
            </el-button>
            <el-button type="danger" size="small" @click="batchDeleteUsers('teacher')" :disabled="selectedTeachers.length === 0">
              删除选中{{ selectedTeachers.length > 0 ? `（${selectedTeachers.length}）` : '' }}
            </el-button>
          </div>
        </div>
      </template>
      <el-table :data="teacherUsers" v-loading="loading" stripe @selection-change="handleTeacherSelection" style="width: 100%">
        <el-table-column type="selection" width="50" />
        <el-table-column prop="username" label="账号" width="150" />
        <el-table-column label="姓名" width="150">
          <template #default="{ row }">
            {{ row.real_name || row.username }}
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="showEditDialog(row)">编辑</el-button>
            <el-button type="warning" link @click="resetPassword(row)">重置密码</el-button>
            <el-button type="danger" link @click="deleteUser(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 学生 -->
    <el-card>
      <template #header>
        <div class="card-header">
          <span><el-tag type="success" style="margin-right: 8px">学生</el-tag></span>
          <div>
            <el-button type="primary" size="small" @click="showAddDialog('student')">
              <el-icon><Plus /></el-icon>
              添加学生
            </el-button>
            <el-button type="danger" size="small" @click="batchDeleteUsers('student')" :disabled="selectedStudents.length === 0">
              删除选中{{ selectedStudents.length > 0 ? `（${selectedStudents.length}）` : '' }}
            </el-button>
          </div>
        </div>
      </template>
      <el-table :data="studentUsers" v-loading="loading" stripe @selection-change="handleStudentSelection" style="width: 100%">
        <el-table-column type="selection" width="50" :selectable="row => authStore.userRole === 'admin' || row.created_by === authStore.user?.id" />
        <el-table-column prop="username" label="账号" width="150" />
        <el-table-column label="姓名" width="150">
          <template #default="{ row }">
            {{ row.real_name || row.username }}
          </template>
        </el-table-column>
        <el-table-column label="管理者" width="150">
          <template #default="{ row }">
            {{ row.manager_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="showEditDialog(row)" v-if="authStore.userRole === 'admin' || row.can_edit">编辑</el-button>
            <el-button type="warning" link @click="resetPassword(row)" v-if="authStore.userRole === 'admin' || row.can_edit">重置密码</el-button>
            <el-button type="danger" link @click="deleteUser(row)" v-if="authStore.userRole === 'admin' || row.created_by === authStore.user?.id">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <!-- 添加对话框（单个/批量 tabs） -->
    <el-dialog v-model="dialogVisible" :title="editUser ? '编辑用户' : (form.role === 'teacher' ? '添加教师' : '添加学生')" width="500px">
      <!-- 编辑模式：显示姓名和管理者（仅管理员编辑学生时） -->
      <el-form v-if="editUser" :model="form" :rules="rules" ref="formRef" label-width="100px" hide-required-asterisk>
        <el-form-item label="姓名" prop="real_name">
          <el-input v-model="form.real_name" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="管理者" v-if="authStore.userRole === 'admin' && editUser?.role === 'student'">
          <el-select v-model="form.manager_id" placeholder="请选择管理者" style="width: 100%">
            <el-option
              v-for="user in managerOptions"
              :key="user.id"
              :label="user.real_name || user.username"
              :value="user.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      
      <!-- 添加模式：批量添加 -->
      <el-form v-else label-width="100px">
        <el-form-item :label="form.role === 'teacher' ? '教师名单' : '学生名单'">
          <el-input
            v-model="batchNames"
            type="textarea"
            :rows="10"
            :placeholder="`请输入${form.role === 'teacher' ? '教师' : '学生'}姓名，每行一个\n例如：\n张三\n李四\n王五`"
          />
        </el-form-item>
        <el-form-item>
          <div class="hint-text">
            系统将自动为{{ form.role === 'teacher' ? '教师' : '学生' }}生成账号，初始密码与账号相同
          </div>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="editUser ? handleEditSubmit() : handleBatchSubmit()" :loading="submitting">
          {{ editUser ? '保存' : '生成' }}
        </el-button>
      </template>
    </el-dialog>
    
    <!-- 批量生成结果对话框 -->
    <el-dialog v-model="batchResultVisible" title="生成结果" width="500px">
      <div class="batch-result">
        <p>成功生成 {{ batchResult.success.length }} 个账号</p>
        <el-table :data="batchResult.success" size="small" max-height="300">
          <el-table-column prop="real_name" label="姓名" width="100" />
          <el-table-column prop="username" label="账号" width="120" />
          <el-table-column prop="password" label="密码" />
        </el-table>
        <div v-if="batchResult.failed.length > 0" style="margin-top: 15px">
          <p style="color: #f56c6c">失败 {{ batchResult.failed.length }} 个</p>
          <ul>
            <li v-for="(name, index) in batchResult.failed" :key="index">{{ name }}</li>
          </ul>
        </div>
      </div>
      
      <template #footer>
        <el-button type="primary" @click="batchResultVisible = false">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../utils/api'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()

const loading = ref(false)
const submitting = ref(false)
const users = ref([])
const dialogVisible = ref(false)
const editUser = ref(null)
const formRef = ref()
const managerOptions = ref([])

const batchDialogVisible = ref(false)
const batchSubmitting = ref(false)
const batchRole = ref('student')
const batchNames = ref('')
const addTab = ref('single')
const batchResultVisible = ref(false)
const batchResult = reactive({
  success: [],
  failed: []
})

const currentUserId = computed(() => authStore.user?.id)
const isTeacherOrAdmin = computed(() => ['admin', 'teacher'].includes(authStore.userRole))

const adminUsers = computed(() => users.value.filter(u => u.role === 'admin'))
const teacherUsers = computed(() => users.value.filter(u => u.role === 'teacher'))
const studentUsers = computed(() => users.value.filter(u => u.role === 'student'))

const form = reactive({
  username: '',
  real_name: '',
  password: '',
  role: 'student',
  manager_id: null
})

const rules = {
  real_name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }]
}

async function loadUsers() {
  loading.value = true
  try {
    const res = await api.get('/auth/users')
    users.value = res.users
  } catch (error) {
    // 错误已处理
  } finally {
    loading.value = false
  }
}

function showAddDialog(role = 'student') {
  editUser.value = null
  form.real_name = ''
  form.password = ''
  form.role = role
  addTab.value = 'single'
  batchNames.value = ''
  dialogVisible.value = true
}

async function showEditDialog(user) {
  editUser.value = user
  form.username = user.username
  form.real_name = user.real_name || ''
  form.password = ''
  form.role = user.role
  form.manager_id = user.created_by || null
  
  // 加载管理者选项（教师和管理员）
  if (authStore.userRole === 'admin' && user.role === 'student') {
    try {
      const res = await api.get('/auth/users')
      managerOptions.value = res.users.filter(u => u.role === 'teacher' || u.role === 'admin')
    } catch (error) {
      managerOptions.value = []
    }
  }
  
  dialogVisible.value = true
}

async function handleEditSubmit() {
  // 姓名为空时禁止保存
  if (!form.real_name || !form.real_name.trim()) {
    ElMessage.warning('姓名不能为空')
    return
  }

  submitting.value = true
  try {
    const data = { real_name: form.real_name.trim() }
    // 管理员编辑学生时，可以修改管理者
    if (authStore.userRole === 'admin' && editUser.value.role === 'student' && form.manager_id !== null) {
      data.manager_id = form.manager_id
    }
    await api.put(`/auth/users/${editUser.value.id}`, data)
    ElMessage.success('修改成功')
    dialogVisible.value = false
    loadUsers()
  } catch (error) {
    // 错误已处理
  } finally {
    submitting.value = false
  }
}

async function handleSingleSubmit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  
  submitting.value = true
  try {
    const res = await api.post('/auth/register', {
      real_name: form.real_name,
      role: form.role,
      created_by: authStore.user?.id
    })
    const { username, password } = res
    ElMessage.success(`添加成功，账号：${username}，默认密码：${password}`)
    dialogVisible.value = false
    loadUsers()
  } catch (error) {
    // 错误已处理
  } finally {
    submitting.value = false
  }
}

function showBatchDialog(role = 'student') {
  batchRole.value = role
  batchNames.value = ''
  batchDialogVisible.value = true
}

async function handleBatchSubmit() {
  const names = batchNames.value.split('\n').map(n => n.trim()).filter(n => n)
  
  if (names.length === 0) {
    ElMessage.warning(`请输入至少一个${form.role === 'teacher' ? '教师' : '学生'}姓名`)
    return
  }
  
  submitting.value = true
  batchResult.success = []
  batchResult.failed = []
  
  try {
    const role = form.role
    
    // 批量创建账号
    for (const name of names) {
      try {
        const res = await api.post('/auth/register', {
          real_name: name,
          role,
          created_by: authStore.user?.id
        })
        batchResult.success.push({
          real_name: name,
          username: res.user.username,
          password: res.password
        })
      } catch (error) {
        batchResult.failed.push(name)
      }
    }
    
    dialogVisible.value = false
    batchResultVisible.value = true
    loadUsers()
    
    if (batchResult.success.length > 0) {
      ElMessage.success(`成功生成 ${batchResult.success.length} 个${form.role === 'teacher' ? '教师' : '学生'}账号`)
    }
  } catch (error) {
    // 错误已处理
  } finally {
    submitting.value = false
  }
}

async function resetPassword(user) {
  try {
    await ElMessageBox.confirm('确定将该用户密码重置为默认密码？', '重置密码', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    const password = user.username  // 重置为账号本身
    await api.put(`/auth/users/${user.id}`, { password, reset_password: true })
    ElMessage.success(`密码已重置为：${password}`)
  } catch (error) {
    if (error !== 'cancel') {
      // 错误已处理
    }
  }
}

const selectedStudents = ref([])
const selectedTeachers = ref([])

function handleStudentSelection(selection) {
  selectedStudents.value = selection
}

function handleTeacherSelection(selection) {
  selectedTeachers.value = selection
}

async function batchDeleteUsers(role) {
  const selected = role === 'student' ? selectedStudents.value : selectedTeachers.value
  if (selected.length === 0) return
  // 教师只能删除自己创建的学生
  if (role === 'student' && authStore.userRole === 'teacher') {
    const canDeleteAll = selected.every(u => u.created_by === authStore.user?.id)
    if (!canDeleteAll) {
      ElMessage.warning('只能删除自己创建的学生')
      return
    }
  }
  const count = selected.length
  const roleLabel = role === 'student' ? '学生账号' : '教师账号'
  const confirmText = `确认删除${count}个${roleLabel}`
  try {
    const { value } = await ElMessageBox.prompt(
      `请输入"${confirmText}"以确认删除`,
      `批量删除${roleLabel}`,
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
        inputPattern: new RegExp(`^确认删除\\d+个${roleLabel}$`),
        inputErrorMessage: '输入内容不匹配'
      }
    )
    if (value === confirmText) {
      let successCount = 0
      for (const user of selected) {
        try {
          await api.delete(`/auth/users/${user.id}`)
          successCount++
        } catch (error) {
          // 单个失败跳过
        }
      }
      ElMessage.success(`已删除 ${successCount} 个${roleLabel}`)
      if (role === 'student') selectedStudents.value = []
      else selectedTeachers.value = []
      loadUsers()
    }
  } catch (error) {
    if (error !== 'cancel') {
      // 错误已处理
    }
  }
}

async function deleteUser(user) {
  const displayName = user.real_name || user.username
  const confirmText = `确认删除${displayName}`
  try {
    const { value } = await ElMessageBox.prompt(
      `请输入"${confirmText}"以确认删除`,
      '删除用户',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
        inputPattern: new RegExp(`^${confirmText}$`),
        inputErrorMessage: '输入内容不匹配'
      }
    )
    if (value === confirmText) {
      await api.delete(`/auth/users/${user.id}`)
      ElMessage.success('删除成功')
      loadUsers()
    }
  } catch (error) {
    if (error !== 'cancel') {
      // 错误已处理
    }
  }
}

function roleTag(role) {
  const tags = { admin: 'danger', teacher: 'warning', student: 'success' }
  return tags[role] || ''
}

function roleLabel(role) {
  const labels = { admin: '管理员', teacher: '教师', student: '学生' }
  return labels[role] || role
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

onMounted(() => {
  loadUsers()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.hint-text {
  color: #909399;
  font-size: 12px;
}

.batch-result {
  max-height: 400px;
  overflow-y: auto;
}
</style>
