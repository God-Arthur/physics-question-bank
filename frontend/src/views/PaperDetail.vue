<template>
  <div class="paper-detail-page" v-loading="loading">
    <!-- 顶部导航 -->
    <div class="page-header">
      <el-button @click="$router.push('/questions')">←返回题库</el-button>
    </div>

    <!-- 试卷标题区域 -->
    <div class="title-area">
      <template v-if="editingTitle">
        <el-input
          ref="titleInputRef"
          v-model="paperName"
          size="large"
          style="max-width: 600px"
          @blur="saveTitle"
          @keyup.enter="saveTitle"
        />
      </template>
      <template v-else>
        <h1 class="paper-title">{{ paperName }}</h1>
        <el-button type="primary" link @click="startEditTitle">编辑</el-button>
      </template>
      <el-button type="success" @click="showPublishDialog = true" style="margin-left: auto">发布到班级</el-button>
    </div>

    <!-- 试卷信息栏 -->
    <div class="paper-info-bar">
      <span v-if="paperInfo.showInstitute" class="info-item">
        <el-icon style="margin-right: 4px"><OfficeBuilding /></el-icon>
        机构：{{ paperInfo.institute }}
      </span>
      <span class="info-item">
        <el-icon style="margin-right: 4px"><Calendar /></el-icon>
        年份：{{ paperInfo.year }}
      </span>
      <span class="info-item">
        <el-icon style="margin-right: 4px"><User /></el-icon>
        作者：{{ paperInfo.authors }}
      </span>
      <span class="info-item">
        总分：{{ paperInfo.totalScore }} 分
      </span>
      <span class="info-item">
        <el-icon style="margin-right: 4px"><Star /></el-icon>
        难度：{{ paperInfo.difficulty.toFixed(2) }}
      </span>
    </div>

    <!-- 题目列表 -->
    <div v-if="questions.length > 0">
      <div v-for="(q, index) in questions" :key="q.id" class="question-block">
        <div class="question-block-header">
          <el-tag type="primary" size="small">第{{ index + 1 }}题</el-tag>
          <el-tag size="small" type="info" style="margin-left: 6px">
            {{ questionTypeLabel(q.question_type) }}
          </el-tag>
          <el-tag size="small" type="warning" style="margin-left: 4px">
            难度: {{ q.difficulty?.toFixed(1) }}
          </el-tag>
          <el-tag size="small" type="success" style="margin-left: 4px">
            {{ q.default_score || 40 }}分
          </el-tag>
          <span class="q-title">{{ q.question_title || '-' }}</span>
          <el-button type="primary" link size="small" style="margin-left: auto" @click="editQuestion(q)">
            编辑
          </el-button>
          <el-button type="danger" link size="small" style="margin-left: 4px" @click="deleteQuestion(q)">
            删除
          </el-button>
        </div>

        <div class="question-split-view">
          <!-- 左栏：题干（LaTeX渲染） -->
          <div class="panel">
            <div class="panel-header">题干</div>
            <div class="panel-body">
              <div class="latex-content" v-html="renderLatex(q.content)"></div>
              <div class="content-images" v-if="getContentImages(q).length > 0">
                <el-image
                  v-for="(img, i) in getContentImages(q)"
                  :key="i"
                  :src="img.url"
                  fit="contain"
                  :class="img.sizeClass"
                  style="margin-bottom: 8px; display: block"
                  :preview-src-list="getContentImages(q).map(x => x.url)"
                />
              </div>
            </div>
          </div>

          <!-- 右栏：答案（LaTeX渲染） -->
          <div class="panel">
            <div class="panel-header">答案</div>
            <div class="panel-body">
              <div class="latex-content" v-html="renderLatex(q.answer)"></div>
              <div class="content-images" v-if="getAnswerImages(q).length > 0">
                <el-image
                  v-for="(img, i) in getAnswerImages(q)"
                  :key="i"
                  :src="img.url"
                  fit="contain"
                  :class="img.sizeClass"
                  style="margin-bottom: 8px; display: block"
                  :preview-src-list="getAnswerImages(q).map(x => x.url)"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <el-empty v-else description="暂无题目" />

    <!-- 发布对话框 -->
    <el-dialog v-model="showPublishDialog" title="发布到班级" width="500px">
      <el-form label-width="100px">
        <el-form-item label="考试班级" required>
          <el-select v-model="publishForm.class_id" placeholder="选择考试班级" style="width: 100%">
            <el-option
              v-for="cls in classList"
              :key="cls.id"
              :label="cls.name"
              :value="cls.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="考试日期" required>
          <el-date-picker
            v-model="publishForm.exam_date"
            type="date"
            placeholder="选择考试日期"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="考试时间" required>
          <div style="display: flex; gap: 12px;">
            <el-time-picker
              v-model="publishForm.start_time"
              placeholder="开始时间"
              format="HH:mm"
              value-format="HH:mm"
              :clearable="false"
              style="flex: 1"
            />
            <el-time-picker
              v-model="publishForm.end_time"
              placeholder="结束时间"
              format="HH:mm"
              value-format="HH:mm"
              :clearable="false"
              style="flex: 1"
            />
          </div>
        </el-form-item>
        <el-form-item label=" ">
          <el-checkbox v-model="publishForm.allow_view_after_exam">
            考试结束后允许学生查看试卷
          </el-checkbox>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showPublishDialog = false">取消</el-button>
        <el-button type="primary" @click="handlePublish" :loading="publishing">发布</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../utils/api'
import { useAuthStore } from '../stores/auth'
import { renderLatex } from '../utils/latex'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const loading = ref(false)
const paperName = ref('')
const questions = ref([])
const editingTitle = ref(false)
const titleInputRef = ref(null)
const instituteList = ref([])

// 发布对话框
const showPublishDialog = ref(false)
const publishing = ref(false)
const classList = ref([])
const publishForm = reactive({
  class_id: '',
  exam_date: '',
  start_time: '',
  end_time: '',
  allow_view_after_exam: false
})

// 加载机构列表（从题目数据中提取，避免额外API调用）
function loadInstitutesFromQuestions() {
  // 从已加载的题目中提取机构信息
  const institutes = new Map()
  questions.value.forEach(q => {
    if (q.source_institute) {
      // 优先使用 source_institute_name，如果没有则尝试从 source_info 解析
      let name = q.source_institute_name
      if (!name && q.source_info) {
        // 尝试从 source_info 解析机构名称
        const info = typeof q.source_info === 'string' ? JSON.parse(q.source_info) : q.source_info
        name = info?.institute_name
      }
      institutes.set(q.source_institute, {
        code: q.source_institute,
        name: name || q.source_institute
      })
    }
  })
  instituteList.value = Array.from(institutes.values())
}

// 试卷信息
const paperInfo = computed(() => {
  // 从题目数据中实时提取所有机构信息（去重）
  const instituteMap = new Map()
  questions.value.forEach(q => {
    if (q.source_institute) {
      const name = q.source_institute_name || q.source_institute
      instituteMap.set(q.source_institute, { code: q.source_institute, name })
    }
  })
  
  const years = [...new Set(questions.value.map(q => q.year).filter(Boolean))]
  const authors = [...new Set(questions.value.map(q => q.author).filter(Boolean))]
  const totalScore = questions.value.reduce((sum, q) => sum + (q.default_score || 0), 0)
  
  // 计算试卷难度系数（所有题目难度的加权平均）
  let weightedDifficulty = 0
  let totalWeight = 0
  questions.value.forEach(q => {
    const score = q.default_score || 40
    const diff = q.difficulty || 0
    weightedDifficulty += score * diff
    totalWeight += score
  })
  const difficulty = totalWeight > 0 ? (weightedDifficulty / totalWeight) : 0
  
  // 判断是否全是历年真题（决定是否显示机构）
  const allPastExam = questions.value.length > 0 && questions.value.every(q => q.source_type === 'past_exam')
  const showInstitute = !allPastExam
  
  // 将机构代码映射为中文名称（格式：中文名称（三字代码））
  const instituteNames = []
  instituteMap.forEach((inst, code) => {
    if (inst.name && inst.name !== code) {
      instituteNames.push(`${inst.name}（${code}）`)
    } else {
      instituteNames.push(code)
    }
  })
  
  return {
    institute: instituteNames.length > 0 ? instituteNames.join('，') : '未知',
    year: years.length > 0 ? years.join('，') : '未知',
    authors: authors.length > 0 ? authors.join('，') : '未知',
    totalScore,
    showInstitute,
    difficulty: Math.round(difficulty * 100) / 100
  }
})

function questionTypeLabel(type) {
  const map = { theory: '理论题', experiment: '实验理论题' }
  return map[type] || type || '-'
}

// 获取完整图片URL
function getFullImageUrl(filename) {
  if (!filename) return ''
  if (filename.startsWith('http://') || filename.startsWith('https://')) return filename
  if (filename.startsWith('/')) return filename
  return `/api/questions/images/${filename}`
}

// 获取图片尺寸对应的CSS类名
function getImageSizeClass(size) {
  switch (size) {
    case 'large': return 'image-size-large'
    case 'medium': return 'image-size-medium'
    case 'small': return 'image-size-small'
    default: return 'image-size-medium'
  }
}

function getContentImages(q) {
  if (!q.content_images) return []
  try {
    const imgs = typeof q.content_images === 'string' ? JSON.parse(q.content_images) : q.content_images
    if (!Array.isArray(imgs)) return []
    return imgs.map(item => {
      const filename = typeof item === 'string' ? item : (item.filename || '')
      const size = typeof item === 'object' && item.size ? item.size : 'medium'
      return {
        url: getFullImageUrl(filename),
        sizeClass: getImageSizeClass(size)
      }
    }).filter(item => item.url)
  } catch {
    return []
  }
}

function getAnswerImages(q) {
  if (!q.answer_images) return []
  try {
    const imgs = typeof q.answer_images === 'string' ? JSON.parse(q.answer_images) : q.answer_images
    if (!Array.isArray(imgs)) return []
    return imgs.map(item => {
      const filename = typeof item === 'string' ? item : (item.filename || '')
      const size = typeof item === 'object' && item.size ? item.size : 'medium'
      return {
        url: getFullImageUrl(filename),
        sizeClass: getImageSizeClass(size)
      }
    }).filter(item => item.url)
  } catch {
    return []
  }
}

// 标题编辑
function startEditTitle() {
  editingTitle.value = true
  nextTick(() => {
    titleInputRef.value?.focus()
  })
}

async function saveTitle() {
  editingTitle.value = false
  if (!paperName.value.trim()) {
    ElMessage.warning('标题不能为空')
    return
  }
  try {
    // 更新所有题目的 title 字段
    for (const q of questions.value) {
      await api.put(`/questions/${q.id}`, { title: paperName.value })
    }
    ElMessage.success('标题已更新')
  } catch {
    ElMessage.error('标题更新失败')
  }
}

// 编辑单题
function editQuestion(q) {
  router.push(`/questions/${q.id}/edit?from=${route.params.uuid}`)
}

// 删除单题
async function deleteQuestion(q) {
  try {
    await ElMessageBox.confirm(`确定要删除题目"${q.question_title || '第' + (questions.value.indexOf(q) + 1) + '题'}"吗？`, '确认删除', {
      type: 'warning'
    })
    
    await api.delete(`/questions/${q.id}`)
    ElMessage.success('删除成功')
    await loadPaper()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败：' + (e.message || '未知错误'))
    }
  }
}

// 加载班级列表
async function loadClassList() {
  try {
    const res = await api.get('/classes')
    let classes = res.classes || []
    if (authStore.userRole === 'teacher') {
      classes = classes.filter(c => c.is_mine)
    }
    classList.value = classes.map(c => ({
      id: c.id,
      name: c.display_name || c.name
    }))
  } catch {
    // 错误已处理
  }
}

// 发布到班级
async function handlePublish() {
  if (!publishForm.class_id) {
    ElMessage.warning('请选择考试班级')
    return
  }
  if (!publishForm.exam_date) {
    ElMessage.warning('请选择考试日期')
    return
  }
  if (!publishForm.start_time || !publishForm.end_time) {
    ElMessage.warning('请选择考试时间')
    return
  }

  try {
    await ElMessageBox.confirm(
      '发布后班级内的学生将能看到此考试，确定要发布吗？',
      '确认发布',
      { confirmButtonText: '确定发布', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }

  publishing.value = true
  try {
    const created = await api.post('/papers', {
      title: paperName.value,
      exam_date: publishForm.exam_date,
      start_time: publishForm.start_time,
      end_time: publishForm.end_time,
      allow_view_after_exam: publishForm.allow_view_after_exam,
      questions: questions.value.map(q => ({
        question_id: q.id,
        score: q.default_score || 40
      }))
    })
    await api.post(`/papers/${created.paper.id}/publish`, {
      class_id: publishForm.class_id,
      exam_date: publishForm.exam_date,
      start_time: publishForm.start_time,
      end_time: publishForm.end_time,
      allow_view_after_exam: publishForm.allow_view_after_exam
    })
    ElMessage.success('发布成功')
    showPublishDialog.value = false
  } catch (error) {
    ElMessage.error('发布失败')
  } finally {
    publishing.value = false
  }
}

async function loadPaper() {
  const uuid = route.params.uuid
  if (!uuid) {
    ElMessage.error('无效的试卷ID')
    router.push('/questions')
    return
  }

  loading.value = true
  try {
    const res = await api.get('/questions', { params: { paper_uuid: uuid, per_page: 1 } })
    const allGroups = res.groups || []
    const matchedGroup = allGroups[0] || allGroups.find(g => g.paper_uuid === uuid)

    if (matchedGroup) {
      paperName.value = matchedGroup.paper_name
      questions.value = matchedGroup.questions.map(q => ({ ...q }))
    } else {
      // 如果找不到分组，尝试用uuid作为题目ID加载
      const questionId = uuid.replace(/^P/, '')
      try {
        const qRes = await api.get(`/questions/${questionId}`)
        const firstQ = qRes.question
        paperName.value = firstQ.title || firstQ.question_title || '未命名试卷'
        questions.value = [{ ...firstQ }]
      } catch {
        ElMessage.error('试卷不存在')
        router.push('/questions')
        return
      }
    }
    
    // 从加载的题目中提取机构信息
    loadInstitutesFromQuestions()
  } catch (error) {
    ElMessage.error('加载试卷失败')
    router.push('/questions')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadPaper()
  loadClassList()
})
</script>

<style scoped>
.paper-detail-page {
  padding: 20px;
}

.page-header {
  margin-bottom: 16px;
}

.title-area {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.paper-info-bar {
  display: flex;
  align-items: center;
  gap: 24px;
  margin-bottom: 24px;
  padding: 12px 16px;
  background: #f5f7fa;
  border-radius: 6px;
  font-size: 13px;
  color: #606266;
}

.info-item {
  display: flex;
  align-items: center;
}

.paper-title {
  font-size: 22px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

.question-block {
  margin-bottom: 24px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  overflow: hidden;
}

.question-block-header {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  background: #f5f7fa;
  border-bottom: 1px solid #ebeef5;
}

.q-title {
  margin-left: 12px;
  font-weight: 500;
  color: #303133;
  font-size: 14px;
}

.question-split-view {
  display: flex;
  gap: 0;
  min-height: 200px;
}

.panel {
  flex: 0 0 calc(50% - 8px);
  width: calc(50% - 8px);
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.panel:first-child {
  border-right: 1px solid #ebeef5;
}

.panel-header {
  padding: 8px 16px;
  font-weight: 600;
  font-size: 13px;
  color: #303133;
  background: #fafafa;
  border-bottom: 1px solid #ebeef5;
}

.panel:first-child .panel-header {
  border-left: 3px solid #409EFF;
}

.panel:last-child .panel-header {
  border-left: 3px solid #67c23a;
}

.panel-body {
  padding: 16px;
  flex: 1;
  overflow-y: auto;
  line-height: 1.8;
}

.content-images {
  margin-bottom: 12px;
}

.latex-content {
  font-size: 14px;
}

/* 图片尺寸 */
:deep(.image-size-large) {
  width: 90%;
}

:deep(.image-size-medium) {
  width: 45%;
}

:deep(.image-size-small) {
  width: 30%;
}
</style>
