<template>
  <div class="class-detail-page" v-loading="loading">
    <div class="page-header">
      <el-button @click="$router.push('/classes')">
        <el-icon><ArrowLeft /></el-icon>
        返回
      </el-button>
      <div style="flex: 1"></div>
      <el-button type="danger" @click="handleDelete" v-if="canEdit">删除班级</el-button>
    </div>

    <!-- 班级信息 -->
    <el-card style="margin-bottom: 20px">
      <div class="class-info-row">
        <div style="flex: 1">
          <span class="info-label">班级名称</span>
          <template v-if="editing">
            <el-input v-model="editForm.name" size="small" style="width: 200px" placeholder="请输入班级名称" />
            <el-button type="primary" link size="small" @click="handleEdit" :loading="editSubmitting" style="margin-left: 8px">保存</el-button>
            <el-button link size="small" @click="cancelEdit">取消</el-button>
          </template>
          <template v-else>
            <span>{{ classInfo?.display_name || classInfo?.name }}</span>
            <el-button type="primary" link size="small" @click="startEdit" v-if="canEdit" style="margin-top: 3px">编辑</el-button>
          </template>
          <span class="info-label" style="margin-left: 40px">学生数</span>
          <span>{{ classInfo?.students?.length || 0 }}人</span>
          <span class="info-label" style="margin-left: 40px">创建时间</span>
          <span>{{ formatDate(classInfo?.created_at) }}</span>
        </div>
        <el-button type="danger" link size="small" @click="exitClass" v-if="isStudent">退出班级</el-button>
      </div>
    </el-card>

    <!-- 学生列表 -->
    <el-card>
      <template #header>
        <div class="card-header">
          <span>学生列表</span>
          <el-button type="danger" size="small" @click="batchRemoveStudents" :disabled="selectedStudents.length === 0" v-if="canEdit">
            批量移除{{ selectedStudents.length > 0 ? `（${selectedStudents.length}）` : '' }}
          </el-button>
        </div>
      </template>
      <el-table :data="classInfo?.students || []" stripe @selection-change="handleStudentSelection" v-if="canEdit">
        <el-table-column type="selection" width="50" />
        <el-table-column prop="username" label="账号" width="150" />
        <el-table-column label="姓名" width="150">
          <template #default="{ row }">
            {{ row.real_name || row.username }}
          </template>
        </el-table-column>
        <el-table-column label="加入时间">
          <template #default="{ row }">
            {{ formatDate(row.joined_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" v-if="canEdit">
          <template #default="{ row }">
            <el-button type="danger" link size="small" @click="removeStudent(row)">移除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-table :data="classInfo?.students || []" stripe v-else>
        <el-table-column prop="username" label="账号" width="150" />
        <el-table-column label="姓名" width="150">
          <template #default="{ row }">
            {{ row.real_name || row.username }}
          </template>
        </el-table-column>
        <el-table-column label="加入时间">
          <template #default="{ row }">
            {{ formatDate(row.joined_at) }}
          </template>
        </el-table-column>
      </el-table>
      <div style="margin-top: 15px; text-align: right" v-if="canEdit && !showInvite">
        <el-button type="primary" size="small" @click="toggleInvitePanel">
          <el-icon><Plus /></el-icon>
          邀请学生加入
        </el-button>
      </div>

      <!-- 邀请学生展开区域 -->
      <div v-if="showInvite" class="invite-panel" v-loading="loadingInvite">
        <div class="invite-header">
          <span class="invite-title">选择学生</span>
          <div>
            <el-button type="primary" size="small" @click="handleBatchInvite" :loading="inviting" :disabled="selectedInviteIds.length === 0">
              确认邀请（{{ selectedInviteIds.length }}）
            </el-button>
            <el-button size="small" @click="toggleInvitePanel">取消</el-button>
          </div>
        </div>
        <el-input v-model="inviteSearch" size="small" placeholder="搜索姓名或账号" style="margin-bottom: 10px; width: 250px" />
        <el-table :data="filteredInviteStudents" stripe size="small" @selection-change="handleSelectionChange">
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
              <el-tag v-if="row.invite_status === 'in_class'" type="success" size="small">已在班级</el-tag>
              <el-tag v-else-if="row.invite_status === 'pending'" type="warning" size="small">已邀请</el-tag>
              <el-tag v-else-if="row.invite_status === 'rejected'" type="danger" size="small">已拒绝</el-tag>
              <el-tag v-else type="info" size="small" effect="plain">未邀请</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <!-- 考试列表 -->
    <el-card style="margin-top: 20px">
      <template #header>
        <div class="card-header">
          <span>考试</span>
        </div>
      </template>
      <el-table :data="examList" stripe v-loading="loadingPapers" v-if="examList.length > 0">
        <el-table-column label="试卷标题" min-width="250">
          <template #default="{ row }">
            <div>
              {{ row.title }}
              <div style="font-size: 12px; color: #909399; margin-top: 2px;">
                发布: {{ row.published_at ? new Date(row.published_at).toLocaleString('zh-CN') : '-' }}
                <span v-if="row.scoring_finished"> | 结束: {{ row.finished_at ? new Date(row.finished_at).toLocaleString('zh-CN') : '-' }}</span>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="考试日期" width="120">
          <template #default="{ row }">
            {{ row.exam_date || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="考试时间" width="150">
          <template #default="{ row }">
            {{ row.start_time && row.end_time ? `${row.start_time} - ${row.end_time}` : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="total_score" label="总分" width="80" />
        <el-table-column label="难度系数" width="100">
          <template #default="{ row }">
            {{ row.difficulty?.toFixed(2) || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getExamStatus(row).type" size="small">
              {{ getExamStatus(row).label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button v-if="canEdit" type="primary" link @click="goScore(row)">登记成绩</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loadingPapers && examList.length === 0" description="暂无考试" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../utils/api'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const classId = route.params.id
const loading = ref(false)
const classInfo = ref(null)

// 考试列表
const exams = ref([])

// 考试列表（直接使用后端返回的数据）
const examList = computed(() => exams.value)
const loadingPapers = ref(false)

const canEdit = computed(() => {
  if (authStore.userRole === 'admin') return true
  if (authStore.userRole === 'teacher' && classInfo.value?.teacher_id === authStore.user?.id) return true
  return false
})

const isStudent = computed(() => authStore.userRole === 'student')

// 编辑（内联）
const editing = ref(false)
const editSubmitting = ref(false)
const editForm = reactive({ name: '' })

function startEdit() {
  editForm.name = classInfo.value.name
  editing.value = true
}

function cancelEdit() {
  editing.value = false
}

async function handleEdit() {
  const name = editForm.name.trim()
  if (!name) {
    ElMessage.warning('班级名称不能为空')
    return
  }
  try {
    const res = await api.get('/classes')
    const currentTeacherId = classInfo.value.teacher_id
    const duplicate = res.classes.find(c => c.name === name && c.teacher_id === currentTeacherId && c.id !== parseInt(classId))
    if (duplicate) {
      ElMessage.warning('已存在同名班级')
      return
    }
  } catch (error) {
    // 忽略
  }
  editSubmitting.value = true
  try {
    await api.put(`/classes/${classId}`, { name })
    ElMessage.success('更新成功')
    editing.value = false
    await loadClass()
  } catch (error) {
    // 错误已处理
  } finally {
    editSubmitting.value = false
  }
}

// 邀请学生
const showInvite = ref(false)
const loadingInvite = ref(false)
const inviteStudents = ref([])
const selectedInviteIds = ref([])
const inviting = ref(false)
const inviteSearch = ref('')

// 学生选择（批量移除）
const selectedStudents = ref([])
const removing = ref(false)

const filteredInviteStudents = computed(() => {
  if (!inviteSearch.value) return inviteStudents.value
  const keyword = inviteSearch.value.toLowerCase()
  return inviteStudents.value.filter(s =>
    (s.username && s.username.toLowerCase().includes(keyword)) ||
    (s.real_name && s.real_name.toLowerCase().includes(keyword))
  )
})

async function toggleInvitePanel() {
  if (showInvite.value) {
    showInvite.value = false
    inviteStudents.value = [] // 清空列表
    selectedInviteIds.value = [] // 清空选择
    return
  }
  loadingInvite.value = true
  showInvite.value = true
  try {
    // 使用新接口获取学生邀请状态
    const res = await api.get(`/classes/${classId}/students/invite-status`)
    
    // 将 accepted 状态转换为 in_class 以兼容现有UI
    inviteStudents.value = res.students.map(student => ({
      ...student,
      invite_status: student.invite_status === 'accepted' ? 'in_class' : student.invite_status
    }))
  } catch (error) {
    // 错误已处理
  } finally {
    loadingInvite.value = false
  }
}

// 判断学生是否可选（可邀请）
function isSelectable(row) {
  // 已在班级内或已邀请未回应的不可选
  if (row.invite_status === 'in_class' || row.invite_status === 'pending') {
    return false
  }
  // 已拒绝的可以再次邀请，未邀请的可以邀请
  return true
}

function handleSelectionChange(selection) {
  selectedInviteIds.value = selection.map(s => s.id)
}

async function handleBatchInvite() {
  if (selectedInviteIds.value.length === 0) return
  inviting.value = true
  let successCount = 0
  try {
    for (const studentId of selectedInviteIds.value) {
      try {
        await api.post(`/classes/${classId}/students`, { student_id: studentId })
        successCount++
      } catch (error) {
        // 单个失败跳过
      }
    }
    ElMessage.success(`已向 ${successCount} 名学生发送邀请`)
    selectedInviteIds.value = []
    showInvite.value = false
    await loadClass()
  } catch (error) {
    // 错误已处理
  } finally {
    inviting.value = false
  }
}

async function loadClass() {
  loading.value = true
  try {
    const res = await api.get(`/classes/${classId}`)
    classInfo.value = res.class
  } catch (error) {
    ElMessage.error('加载班级信息失败')
    router.push('/classes')
  } finally {
    loading.value = false
  }
}

async function loadPapers() {
  loadingPapers.value = true
  try {
    // 获取班级考试列表（包含已发布的试卷和已结束登记的快照）
    const res = await api.get(`/classes/${classId}/exams`)
    exams.value = res.exams || []
  } catch (error) {
    // 错误已处理
  } finally {
    loadingPapers.value = false
  }
}

async function handleDelete() {
  const displayName = classInfo.value.display_name || classInfo.value.name
  const confirmText = `确认删除${displayName}`
  try {
    const { value } = await ElMessageBox.prompt(
      `请输入"${confirmText}"以确认删除`,
      '删除班级',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
        inputPattern: new RegExp(`^${confirmText}$`),
        inputErrorMessage: '输入内容不匹配'
      }
    )
    if (value === confirmText) {
      await api.delete(`/classes/${classId}`)
      ElMessage.success('删除成功')
      router.push('/classes')
    }
  } catch (error) {
    if (error !== 'cancel') {
      // 错误已处理
    }
  }
}

function handleStudentSelection(selection) {
  selectedStudents.value = selection
}

async function removeStudent(student) {
  const confirmText = `确认移除${student.real_name || student.username}`
  try {
    const { value } = await ElMessageBox.prompt(
      `请输入"${confirmText}"以确认移除`,
      '确认移除',
      {
        confirmButtonText: '移除',
        cancelButtonText: '取消',
        type: 'warning',
        inputPattern: new RegExp(`^${confirmText}$`),
        inputErrorMessage: '输入内容不匹配'
      }
    )
    if (value === confirmText) {
      await api.delete(`/classes/${classId}/students/${student.id}`)
      ElMessage.success('移除成功')
      await loadClass()
    }
  } catch (error) {
    if (error !== 'cancel') {
      // 错误已处理
    }
  }
}

async function batchRemoveStudents() {
  if (selectedStudents.value.length === 0) return
  const count = selectedStudents.value.length
  const confirmText = `确认移除${count}名学生`
  try {
    const { value } = await ElMessageBox.prompt(
      `请输入"${confirmText}"以确认移除`,
      '批量移除',
      {
        confirmButtonText: '移除',
        cancelButtonText: '取消',
        type: 'warning',
        inputPattern: new RegExp(`^确认移除\\d+名学生$`),
        inputErrorMessage: '输入内容不匹配'
      }
    )
    if (value === confirmText) {
      removing.value = true
      let successCount = 0
      for (const student of selectedStudents.value) {
        try {
          await api.delete(`/classes/${classId}/students/${student.id}`)
          successCount++
        } catch (error) {
          // 单个失败跳过
        }
      }
      ElMessage.success(`成功移除 ${successCount} 名学生`)
      selectedStudents.value = []
      await loadClass()
    }
  } catch (error) {
    if (error !== 'cancel') {
      // 错误已处理
    }
  } finally {
    removing.value = false
  }
}

async function exitClass() {
  const confirmText = '确认退出班级'
  try {
    const { value } = await ElMessageBox.prompt(
      `请输入"${confirmText}"以确认退出`,
      '退出班级',
      {
        confirmButtonText: '退出',
        cancelButtonText: '取消',
        type: 'warning',
        inputPattern: new RegExp(`^${confirmText}$`),
        inputErrorMessage: '输入内容不匹配'
      }
    )
    if (value === confirmText) {
      await api.delete(`/classes/${classId}/students/${authStore.user?.id}`)
      ElMessage.success('已退出班级')
      router.push('/classes')
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

function getExamStatus(paper) {
  if (!paper.exam_date || !paper.end_time) {
    return { label: '未开始', type: 'info' }
  }
  const now = new Date()
  const examStart = new Date(`${paper.exam_date}T${paper.start_time || '00:00'}:00`)

  // 判断结束时间是否跨天（结束时间早于开始时间）
  let examEndDate = paper.exam_date
  if (paper.start_time && paper.end_time && paper.end_time < paper.start_time) {
    // 跨天，结束日期加1天
    const nextDate = new Date(`${paper.exam_date}T00:00:00`)
    nextDate.setDate(nextDate.getDate() + 1)
    examEndDate = nextDate.toISOString().split('T')[0]
  }
  const examEnd = new Date(`${examEndDate}T${paper.end_time}:00`)

  if (now < examStart) {
    return { label: '未开始', type: 'info' }
  } else if (now > examEnd) {
    return { label: '已结束', type: 'success' }
  } else {
    return { label: '进行中', type: 'warning' }
  }
}

function goScore(exam) {
  // 跳转到成绩登记页面，使用 publish_id
  router.push(`/classes/${classId}/exams/${exam.publish_id}/scores`)
}

onMounted(() => {
  loadClass()
  loadPapers()
})
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.name-cell {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.class-info-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.info-label {
  color: #909399;
  font-size: 14px;
}

.invite-panel {
  margin-top: 15px;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 4px;
  min-height: 300px;
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
