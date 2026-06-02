<template>
  <div class="paper-compose-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ isEdit ? '编辑试卷' : '新建试卷' }}</span>
          <div>
            <el-button @click="goBack">返回</el-button>
            <el-button type="success" @click="publishPaper" :loading="publishing" v-if="isEdit && form.class_id !== ''">发布到班级</el-button>
            <el-button type="primary" @click="savePaper" :loading="submitting">{{ isEdit ? '保存修改' : '确认创建' }}</el-button>
          </div>
        </div>
      </template>

      <!-- 试卷基本信息 -->
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px" hide-required-asterisk>
        <el-form-item label="试卷标题" prop="title">
          <el-input v-model="form.title" placeholder="请输入试卷标题" />
        </el-form-item>

        <el-form-item label="考试时间" prop="examTime">
          <div style="display: flex; gap: 12px; align-items: center;">
            <el-date-picker
              v-model="form.exam_date"
              type="date"
              placeholder="考试日期"
              value-format="YYYY-MM-DD"
              style="width: 150px"
            />
            <el-time-picker
              v-model="form.start_time"
              placeholder="开始时间"
              format="HH:mm"
              value-format="HH:mm"
              :clearable="false"
              style="width: 110px"
            />
            <el-time-picker
              v-model="form.end_time"
              placeholder="结束时间"
              format="HH:mm"
              value-format="HH:mm"
              :clearable="false"
              style="width: 110px"
            />
          </div>
        </el-form-item>

        <!-- 编辑模式下显示考试班级和允许查看选项 -->
        <template v-if="isEdit">
          <el-form-item label="考试班级">
            <div style="display: flex; gap: 12px; align-items: center;">
              <el-select
                v-model="form.class_id"
                placeholder="选择考试班级"
                clearable
                style="width: 200px"
              >
                <el-option label="无" value="" />
                <el-option
                  v-for="cls in classList"
                  :key="cls.id"
                  :label="cls.name"
                  :value="cls.id"
                />
              </el-select>
              <el-checkbox
                v-model="form.allow_view_after_exam"
                :disabled="!form.class_id"
              >
                考试结束后允许学生查看试卷
              </el-checkbox>
            </div>
          </el-form-item>
        </template>
      </el-form>

      <el-divider />

      <!-- 题目列表 -->
      <div class="questions-list-section" v-if="selectedQuestions.length > 0">
        <div class="section-header">
          <h3>题目列表</h3>
          <div style="display: flex; gap: 20px;">
            <span class="total-score">总分: {{ totalScore }} 分</span>
            <span class="difficulty-score">难度系数: {{ difficultyCoefficient }}</span>
          </div>
        </div>

        <el-table :data="selectedQuestions" style="width: 100%" border>
          <el-table-column label="题号" width="80">
            <template #default="{ $index }">
              {{ $index + 1 }}
            </template>
          </el-table-column>

          <el-table-column label="题目标题" min-width="300">
            <template #default="{ row }">
              {{ row.question_title || row.content?.replace(/<[^>]+>/g, '').substring(0, 100) || '无' }}
            </template>
          </el-table-column>

          <el-table-column label="分数" width="120">
            <template #default="{ row }">
              <el-input-number
                v-model="row.score"
                :min="1"
                :max="100"
                :controls="false"
                size="small"
                @change="onScoreChange"
              />
            </template>
          </el-table-column>

          <el-table-column label="操作" width="100" fixed="right">
            <template #default="{ $index }">
              <el-button
                type="danger"
                size="small"
                link
                @click="removeQuestion($index)"
              >
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- PDF 预览区域 -->
      <div class="pdf-preview-section">
        <div class="section-header">
          <h3>试卷预览</h3>
          <el-button type="primary" size="small" @click="generatePreview" :loading="generatingPdf" :disabled="!canPreview">
            <el-icon><Refresh /></el-icon>
            {{ pdfUrl ? '刷新预览' : '生成预览' }}
          </el-button>
        </div>

        <div v-if="pdfUrl" class="pdf-viewer-container">
          <iframe :src="pdfUrl" class="pdf-viewer" frameborder="0"></iframe>
        </div>
        <el-empty v-else-if="!generatingPdf" :description="canPreview ? '点击上方按钮生成预览' : '请先填写试卷标题和考试日期'" />
        <div v-else class="pdf-loading">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>正在生成PDF预览...</span>
        </div>
      </div>

      <!-- 答案预览区域 -->
      <div class="pdf-preview-section">
        <div class="section-header">
          <h3>答案预览</h3>
        </div>

        <div v-if="answerPdfUrl" class="pdf-viewer-container">
          <iframe :src="answerPdfUrl" class="pdf-viewer" frameborder="0"></iframe>
        </div>
        <el-empty v-else-if="!generatingAnswerPdf" :description="canPreview ? '点击上方按钮生成预览' : '请先填写试卷标题和考试日期'" />
        <div v-else class="pdf-loading">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>正在生成答案PDF...</span>
        </div>
      </div>

    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter, useRoute, onBeforeRouteLeave } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Loading } from '@element-plus/icons-vue'
import api from '../utils/api'
import { useAuthStore } from '../stores/auth'
import { setPdfSessionId, clearPdfSessionId } from '../utils/uploadSession'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const formRef = ref()
const submitting = ref(false)
const publishing = ref(false)
const generatingPdf = ref(false)
const pdfUrl = ref('')
const previewId = ref('')
const generatingAnswerPdf = ref(false)
const answerPdfUrl = ref('')
const answerPreviewId = ref('')
const selectedQuestions = ref([])

// PDF预览会话
const pdfSessionId = ref('')

// 编辑模式
const isEdit = computed(() => !!route.params.id)
const paperId = computed(() => route.params.id)

const classList = ref([])

const form = reactive({
  title: '',
  exam_date: '',
  start_time: '',
  end_time: '',
  class_id: '',
  allow_view_after_exam: false,
  duration: ''
})

const rules = {
  title: [{ required: true, message: '请输入试卷标题', trigger: 'blur' }],
  examTime: [{
    required: true,
    validator: (rule, value, callback) => {
      if (!form.exam_date) {
        callback(new Error('请选择考试日期'))
      } else if (!form.start_time) {
        callback(new Error('请选择开始时间'))
      } else if (!form.end_time) {
        callback(new Error('请选择结束时间'))
      } else {
        callback()
      }
    },
    trigger: 'change'
  }]
}

// 加载班级列表
async function loadClasses() {
  try {
    const res = await api.get('/classes')
    let classes = res.classes || []

    // 教师只能看到自己创建的班级（is_mine=true）
    if (authStore.userRole === 'teacher') {
      classes = classes.filter(c => c.is_mine)
    }
    // 管理员可以看到所有班级，不需要过滤

    classList.value = classes.map(c => ({
      id: c.id,
      name: c.display_name || c.name
    }))
  } catch (error) {
    // 错误已处理
  }
}

const totalScore = computed(() => {
  return selectedQuestions.value.reduce((sum, item) => sum + (item.score || 0), 0)
})

const difficultyCoefficient = computed(() => {
  if (selectedQuestions.value.length === 0 || totalScore.value === 0) return 0
  const totalDifficulty = selectedQuestions.value.reduce((sum, item) => {
    const qDifficulty = item.difficulty || 0
    return sum + (item.score || 0) * qDifficulty
  }, 0)
  return (totalDifficulty / totalScore.value).toFixed(2)
})

const canPreview = computed(() => {
  return !!(form.title && form.exam_date)
})

const questionTypeMap = {
  theory: { label: '理论题', type: 'primary' },
  experiment: { label: '实验理论题', type: 'success' }
}

const questionTypeLabel = (type) => questionTypeMap[type]?.label || type
const questionTypeTag = (type) => questionTypeMap[type]?.type || ''

function truncateContent(content) {
  if (!content) return '-'
  const text = content.replace(/<[^>]+>/g, '')
  return text.length > 100 ? text.substring(0, 100) + '...' : text
}

function getChineseNumber(num) {
  const chineseNums = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十',
                      '十一', '十二', '十三', '十四', '十五']
  return chineseNums[num - 1] || num.toString()
}

function onScoreChange() {
  // 分值变化时自动刷新预览
  if (pdfUrl.value) {
    generatePreview()
  }
}

function removeQuestion(index) {
  selectedQuestions.value.splice(index, 1)
  // 删除题目后刷新预览
  if (pdfUrl.value) {
    generatePreview()
  }
}

// 生成PDF预览
async function generatePreview() {
  if (selectedQuestions.value.length === 0) {
    ElMessage.warning('请至少选择一道题目')
    return
  }

  generatingPdf.value = true
  generatingAnswerPdf.value = true
  try {
    // 初始化PDF预览会话
    if (!pdfSessionId.value) {
      const sessionRes = await api.post('/pdf/session/init')
      pdfSessionId.value = sessionRes.session_id
      setPdfSessionId(sessionRes.session_id)
    }

    // 生成时间信息
    let timeInfo = '（考试时间）'
    if (form.exam_date) {
      const dateParts = form.exam_date.split('-')
      const month = parseInt(dateParts[1])
      const day = parseInt(dateParts[2])
      const dateStr = `${dateParts[0]}年${month}月${day}日`
      if (form.start_time) {
        const startStr = form.start_time.substring(0, 5)
        if (form.end_time) {
          const endStr = form.end_time.substring(0, 5)
          timeInfo = `（${dateStr}${startStr}-${endStr}）`
        } else {
          timeInfo = `（${dateStr}${startStr}）`
        }
      } else {
        timeInfo = `（${dateStr}）`
      }
    }

    const res = await api.post('/pdf/preview', {
      title: form.title || '试卷预览',
      time_info: timeInfo,
      session_id: pdfSessionId.value,
      questions: selectedQuestions.value.map(item => ({
        id: item.id,
        question_title: item.question_title,
        default_score: item.default_score,
        score: item.score
      }))
    })

    previewId.value = res.preview_id
    // PDF URL 改为实时编译：/api/pdf/preview/{session_id}/{preview_id}
    pdfUrl.value = `/api/pdf/preview/${pdfSessionId.value}/${res.preview_id}`

    // 同时生成答案预览
    generateAnswerPreview(timeInfo)
  } catch (error) {
    ElMessage.error('PDF预览生成失败')
  } finally {
    generatingPdf.value = false
  }
}

// 生成答案PDF预览
async function generateAnswerPreview(timeInfo) {
  if (selectedQuestions.value.length === 0) return

  generatingAnswerPdf.value = true
  try {
    if (answerPreviewId.value) {
      // 清理旧答案预览
    }

    const res = await api.post('/pdf/answer-preview', {
      title: form.title || '试卷预览',
      time_info: timeInfo,
      session_id: pdfSessionId.value,
      questions: selectedQuestions.value.map(item => ({
        id: item.id,
        question_title: item.question_title,
        default_score: item.default_score,
        score: item.score
      }))
    })

    answerPreviewId.value = res.preview_id
    answerPdfUrl.value = `/api/pdf/preview/${pdfSessionId.value}/${res.preview_id}`
  } catch (error) {
    console.error('答案PDF生成失败', error)
  } finally {
    generatingAnswerPdf.value = false
  }
}

// 删除预览PDF
async function deletePreview(id) {
  try {
    await api.delete(`/pdf/preview/${id}`)
  } catch (error) {
    // 忽略删除错误
  }
}

// 清理PDF预览会话
async function cleanupPdfSession() {
  if (!pdfSessionId.value) return
  try {
    await api.post('/pdf/session/cleanup', { session_id: pdfSessionId.value })
  } catch (e) {
    // 忽略错误
  } finally {
    clearPdfSessionId()
    pdfSessionId.value = ''
    previewId.value = ''
    answerPreviewId.value = ''
  }
}

async function publishPaper() {
  console.log('[PaperCompose] publishPaper called, class_id:', form.class_id)
  if (!form.class_id) {
    ElMessage.warning('请先选择考试班级')
    return
  }
  try {
    console.log('[PaperCompose] showing confirm dialog...')
    await ElMessageBox.confirm(
      '发布后班级内的学生将能看到此考试，确定要发布吗？',
      '确认发布',
      { confirmButtonText: '确定发布', cancelButtonText: '取消', type: 'warning' }
    )
    console.log('[PaperCompose] user confirmed')
  } catch (err) {
    console.log('[PaperCompose] dialog rejected, err:', err)
    return
  }

  publishing.value = true
  try {
    console.log('[PaperCompose] saving paper...')
    // 先保存试卷
    const paperData = {
      title: form.title,
      exam_date: form.exam_date,
      start_time: form.start_time,
      end_time: form.end_time,
      duration: form.duration,
      questions: selectedQuestions.value.map((q, index) => ({
        question_id: q.id,
        score: q.score || q.default_score || 40,
        order: index + 1
      }))
    }
    console.log('[PaperCompose] paperData:', paperData)
    await api.put(`/papers/${paperId.value}`, paperData)
    console.log('[PaperCompose] paper saved, now publishing...')

    // 然后发布
    await api.post(`/papers/${paperId.value}/publish`, {
      class_id: form.class_id,
      allow_view_after_exam: form.allow_view_after_exam
    })
    console.log('[PaperCompose] published successfully')
    ElMessage.success('发布成功')
    // 跳转到试卷列表
    router.push('/papers')
  } catch (error) {
    console.error('[PaperCompose] publish error:', error)
    if (error.response?.data?.error) {
      ElMessage.error(error.response.data.error)
    } else {
      ElMessage.error('发布失败')
    }
  } finally {
    publishing.value = false
  }
}

function goBack() {
  cleanupPdfSession()
  if (isEdit.value) {
    window.location.href = '/papers'
  } else {
    window.location.href = '/questions'
  }
}


async function savePaper() {
  console.log('[PaperCompose] savePaper clicked')
  if (selectedQuestions.value.length === 0) {
    ElMessage.warning('请至少选择一道题目')
    return
  }

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    submitting.value = true
    try {
      const paperData = {
        title: form.title,
        exam_date: form.exam_date,
        start_time: form.start_time,
        end_time: form.end_time,
        preview_id: previewId.value,  // 试卷预览ID，用于读取tex文件
        answer_preview_id: answerPreviewId.value,  // 答案预览ID
        pdf_session_id: pdfSessionId.value,  // PDF预览会话ID
        questions: selectedQuestions.value.map(item => {
          // 保存原始题目数据给后端使用
          return {
            question_id: item.id,
            question_title: item.question_title,
            default_score: item.default_score,
            score: item.score  // 用户可以修改的分数
          }
        })
      }

      if (isEdit.value) {
        await api.put(`/papers/${paperId.value}`, paperData)
        ElMessage.success('试卷修改成功')
      } else {
        await api.post('/papers', paperData)
        ElMessage.success('试卷创建成功')
      }

      // 清理预览会话（后端已读取tex，可以安全清理）
      await cleanupPdfSession()

      // 清除sessionStorage中的选题数据
      sessionStorage.removeItem('composeQuestions')

      window.location.href = '/papers'
    } catch (error) {
      // 错误已处理
    } finally {
      submitting.value = false
    }
  })
}

// 编辑模式：加载已有试卷数据
async function loadPaperData() {
  if (!isEdit.value) return

  try {
    const res = await api.get(`/papers/${paperId.value}`)
    const paper = res.paper

    form.title = paper.title
    form.exam_date = paper.exam_date || ''
    form.start_time = paper.start_time || ''
    form.end_time = paper.end_time || ''

    // 加载题目列表
    if (paper.questions) {
      selectedQuestions.value = paper.questions.map(item => ({
        id: item.question.id,
        question_title: item.question.question_title || item.question.title,
        content: item.question.content,
        answer: item.question.answer,
        default_score: item.question.default_score,
        difficulty: item.question.difficulty,
        score: item.score
      }))
    }
  } catch (error) {
    ElMessage.error('加载试卷数据失败')
    window.location.href = '/papers'
  }
}

onMounted(() => {
  // 编辑模式：加载已有试卷数据
  if (isEdit.value) {
    loadPaperData()
    loadClasses()
  } else {
    // 新建模式：从sessionStorage加载已选题目
    const stored = sessionStorage.getItem('composeQuestions')
    if (stored) {
      try {
        const questions = JSON.parse(stored)
        selectedQuestions.value = questions.map(q => ({
          ...q,
          score: q.score || q.default_score || 40
        }))
      } catch (e) {
        console.error('解析选题数据失败', e)
      }
    }
  }
})

// 关闭标签页/刷新：尽力清理
function _onBeforeUnload() {
  if (pdfSessionId.value) {
    // 使用 sendBeacon 确保请求发出
    const payload = JSON.stringify({ session_id: pdfSessionId.value })
    navigator.sendBeacon('/api/pdf/session/cleanup-noauth', new Blob([payload], { type: 'application/json' }))
  }
}
window.addEventListener('beforeunload', _onBeforeUnload)
onBeforeUnmount(() => window.removeEventListener('beforeunload', _onBeforeUnload))

// 离开此页面时强制全页面刷新，确保目标页面正确渲染
onBeforeRouteLeave(async (to, from, next) => {
  sessionStorage.removeItem('composeQuestions')
  sessionStorage.removeItem('returnToComposeMode')
  
  // 清理PDF预览会话
  await cleanupPdfSession()
  
  // 使用全页面刷新跳转，避免 Vue Router 组件复用问题
  window.location.href = to.fullPath
  // 不调用 next()，因为 window.location.href 会接管导航
})

onBeforeUnmount(() => {
  // 兜底清理（正常情况下 onBeforeRouteLeave 已处理）
  try {
    sessionStorage.removeItem('composeQuestions')
    sessionStorage.removeItem('returnToComposeMode')
  } catch (e) {}
  // 用户跳走时清理PDF预览会话
  if (pdfSessionId.value) {
    api.post('/pdf/session/cleanup', { session_id: pdfSessionId.value }).catch(() => {})
  }
})
</script>

<style scoped>
.paper-compose-page {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.section-header h3 {
  margin: 0;
  font-size: 16px;
  color: #303133;
}

.pdf-preview-section {
  margin: 20px 0;
}

.pdf-viewer-container {
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  overflow: hidden;
}

.pdf-viewer {
  width: 100%;
  height: 600px;
}

.questions-list-section {
  margin: 20px 0;
}

.total-score {
  font-size: 14px;
  color: #f56c6c;
  font-weight: bold;
}

/* 题目列表表格样式 */
.questions-list-section .el-table {
  font-size: 13px;
}

.questions-list-section .el-table th {
  background-color: #f5f7fa;
  color: #606266;
  font-weight: 600;
}

.questions-list-section .el-table .cell {
  padding: 8px 0;
}

/* 分数输入框样式 */
.questions-list-section .el-input-number {
  width: 100%;
}

.questions-list-section .el-input-number .el-input__wrapper {
  padding: 1px 8px;
}

.questions-list-section .el-input-number .el-input__inner {
  text-align: center;
}

.pdf-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: #909399;
}

.pdf-loading .el-icon {
  font-size: 32px;
  margin-bottom: 10px;
}

.questions-list-section {
  margin: 20px 0;
}

.questions-list-section .section-header {
  justify-content: space-between;
}

.questions-list-section .section-header h3 {
  margin: 0;
  font-size: 16px;
  color: #303133;
}

.total-score {
  font-size: 14px;
  color: #409eff;
  font-weight: 500;
}

.question-content {
  font-size: 13px;
  color: #606266;
  line-height: 1.5;
}
</style>
