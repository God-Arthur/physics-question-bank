<template>
  <div class="class-create-page">
    <div class="page-header">
      <el-button @click="$router.push('/classes')">
        <el-icon><ArrowLeft /></el-icon>
        返回
      </el-button>
    </div>

    <el-card style="max-width: 800px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="80px" hide-required-asterisk>
        <el-form-item label="班级名称" prop="name" class="name-form-item">
          <el-input v-model="form.name" placeholder="请输入班级名称" style="width: 300px" />
        </el-form-item>
      </el-form>

      <!-- 邀请学生区域 -->
      <div class="invite-section">
        <div class="invite-header">
          <span class="invite-title">邀请学生加入</span>
          <div>
            <el-button type="primary" size="small" @click="handleCreateAndInvite" :loading="submitting">
              创建班级{{ selectedInviteIds.length > 0 ? `并邀请（${selectedInviteIds.length}）` : '' }}
            </el-button>
          </div>
        </div>
        <el-input v-model="inviteSearch" size="small" placeholder="搜索姓名或账号" style="margin-bottom: 10px; width: 250px" />
        <el-table :data="filteredInviteStudents" stripe size="small" v-loading="loadingStudents" style="width: 100%" @selection-change="handleSelectionChange">
          <el-table-column type="selection" width="50" :selectable="isSelectable" />
          <el-table-column prop="username" label="账号" width="130" />
          <el-table-column label="姓名" width="130">
            <template #default="{ row }">
              {{ row.real_name || row.username }}
            </template>
          </el-table-column>
          <el-table-column label="管理者" width="130">
            <template #default="{ row }">
              {{ row.manager_name || '-' }}
            </template>
          </el-table-column>
          <el-table-column label="状态" width="120">
            <template #default="{ row }">
              <el-tag v-if="row.invite_status === 'accepted'" type="success" size="small">已在班级</el-tag>
              <el-tag v-else-if="row.invite_status === 'pending'" type="warning" size="small">已邀请</el-tag>
              <el-tag v-else-if="row.invite_status === 'rejected'" type="info" size="small">已拒绝</el-tag>
              <el-tag v-else type="info" size="small" effect="plain">未邀请</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../utils/api'

const router = useRouter()

const formRef = ref()
const submitting = ref(false)
const loadingStudents = ref(false)
const form = reactive({ name: '' })
const rules = {
  name: [{ required: true, message: '请输入班级名称', trigger: 'blur' }]
}

// 邀请学生
const inviteStudents = ref([])
const selectedInviteIds = ref([])
const inviteSearch = ref('')

const filteredInviteStudents = computed(() => {
  if (!inviteSearch.value) return inviteStudents.value
  const keyword = inviteSearch.value.toLowerCase()
  return inviteStudents.value.filter(s =>
    (s.username && s.username.toLowerCase().includes(keyword)) ||
    (s.real_name && s.real_name.toLowerCase().includes(keyword))
  )
})

// 判断学生是否可选（可邀请）
function isSelectable(row) {
  // 已在班级内或已邀请未回应的不可选
  if (row.invite_status === 'accepted' || row.invite_status === 'pending') {
    return false
  }
  // 已拒绝的可以再次邀请，未邀请的可以邀请
  return true
}

// 处理选择变化
function handleSelectionChange(selection) {
  selectedInviteIds.value = selection.map(s => s.id)
}

async function loadStudents() {
  loadingStudents.value = true
  try {
    // 使用新接口获取学生邀请状态，class_id=0 表示创建新班级
    const res = await api.get('/classes/0/students/invite-status')
    inviteStudents.value = res.students
  } catch (error) {
    // 错误已处理
  } finally {
    loadingStudents.value = false
  }
}

async function handleCreateAndInvite() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    // 1. 创建班级
    const res = await api.post('/classes', form)
    const classId = res.class.id

    // 2. 批量邀请学生（如果有选择）
    if (selectedInviteIds.value.length > 0) {
      let successCount = 0
      for (const studentId of selectedInviteIds.value) {
        try {
          await api.post(`/classes/${classId}/students`, { student_id: studentId })
          successCount++
        } catch (error) {
          // 单个失败跳过
        }
      }
      ElMessage.success(`创建成功，已向 ${successCount} 名学生发送邀请`)
    } else {
      ElMessage.success('创建成功')
    }
    router.push(`/classes/${classId}`)
  } catch (error) {
    // 错误已处理
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  loadStudents()
})
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
}

.name-form-item :deep(.el-form-item__error) {
  left: 80px;
}

.invite-section {
  margin-top: 20px;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 4px;
}

.invite-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.invite-title {
  font-weight: 600;
  font-size: 14px;
  color: #303133;
}
</style>
