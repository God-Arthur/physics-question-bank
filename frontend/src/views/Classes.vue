<template>
  <div class="classes-page">
    <!-- 操作栏 -->
    <div class="action-bar" v-if="authStore.userRole === 'teacher'">
      <el-checkbox v-model="onlyMine">
        只看我的班级
      </el-checkbox>
    </div>
    
    <!-- 班级邀请通知 -->
    <el-alert
      v-if="isStudent && invitations.length > 0"
      type="info"
      :closable="false"
      style="margin-bottom: 15px"
    >
      <template #title>
        <span>您有 {{ invitations.length }} 条班级邀请待确认</span>
      </template>
      <div v-for="inv in invitations" :key="inv.id" style="margin-top: 8px; display: flex; align-items: center; gap: 10px">
        <span>{{ inv.teacher_name }}-{{ inv.class_name }} 邀请您加入</span>
        <el-button type="primary" size="small" @click="acceptInvitation(inv.id)">同意</el-button>
        <el-button size="small" @click="rejectInvitation(inv.id)">拒绝</el-button>
      </div>
    </el-alert>
    
    <!-- 班级列表 -->
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ isStudent ? '我加入的班级' : '班级列表' }}</span>
          <div>
            <el-button type="primary" size="small" @click="showAddDialog" v-if="isTeacher">
              <el-icon><Plus /></el-icon>
              创建班级
            </el-button>
            <el-button type="danger" size="small" @click="batchDeleteClasses" :disabled="selectedClasses.length === 0" v-if="isTeacher" style="margin-left: 8px">
              删除选中{{ selectedClasses.length > 0 ? `（${selectedClasses.length}）` : '' }}
            </el-button>
          </div>
        </div>
      </template>
      <el-table :data="filteredClasses" v-loading="loading" stripe @selection-change="handleClassSelection">
        <el-table-column type="selection" width="50" :selectable="row => row.is_mine || authStore.userRole === 'admin'" />
        <el-table-column label="班级名称" min-width="300">
          <template #default="{ row }">
            {{ row.display_name || row.name }}
          </template>
        </el-table-column>
        
        <el-table-column prop="student_count" label="学生数" width="100" />
        
        <el-table-column label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="$router.push(`/classes/${row.id}`)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import api from '../utils/api'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const router = useRouter()

const loading = ref(false)
const classes = ref([])
const onlyMine = ref(false)

const isTeacher = computed(() => ['admin', 'teacher'].includes(authStore.userRole))
const isStudent = computed(() => authStore.userRole === 'student')
const invitations = ref([])

const filteredClasses = computed(() => {
  if (!onlyMine.value) return classes.value
  return classes.value.filter(c => c.is_mine)
})

function showAddDialog() {
  router.push('/classes/create')
}

async function loadInvitations() {
  if (!isStudent.value) return
  try {
    const res = await api.get('/classes/invitations')
    invitations.value = res.invitations || []
  } catch (error) {
    // 错误已处理
  }
}

async function acceptInvitation(invitationId) {
  try {
    await api.post(`/classes/invitations/${invitationId}/accept`)
    ElMessage.success('已加入班级')
    await loadInvitations()
    await loadClasses()
  } catch (error) {
    // 错误已处理
  }
}

async function rejectInvitation(invitationId) {
  try {
    await api.post(`/classes/invitations/${invitationId}/reject`)
    ElMessage.info('已拒绝邀请')
    await loadInvitations()
  } catch (error) {
    // 错误已处理
  }
}

async function loadClasses() {
  loading.value = true
  try {
    const res = await api.get('/classes')
    classes.value = res.classes
  } catch (error) {
    // 错误已处理
  } finally {
    loading.value = false
  }
}

const selectedClasses = ref([])

function handleClassSelection(selection) {
  selectedClasses.value = selection
}

async function batchDeleteClasses() {
  if (selectedClasses.value.length === 0) return
  const count = selectedClasses.value.length
  const confirmText = `确认删除${count}个班级`
  try {
    const { value } = await ElMessageBox.prompt(
      `请输入"${confirmText}"以确认删除`,
      '批量删除班级',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
        inputPattern: new RegExp(`^确认删除\\d+个班级$`),
        inputErrorMessage: '输入内容不匹配'
      }
    )
    if (value === confirmText) {
      let successCount = 0
      for (const cls of selectedClasses.value) {
        try {
          await api.delete(`/classes/${cls.id}`)
          successCount++
        } catch (error) {
          // 单个失败跳过
        }
      }
      ElMessage.success(`已删除 ${successCount} 个班级`)
      selectedClasses.value = []
      loadClasses()
    }
  } catch (error) {
    if (error !== 'cancel') {
      // 错误已处理
    }
  }
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

onMounted(() => {
  loadClasses()
  loadInvitations()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.action-bar {
  margin-bottom: 20px;
}

.students-section {
  margin-top: 20px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.section-header h4 {
  margin: 0;
}
</style>
