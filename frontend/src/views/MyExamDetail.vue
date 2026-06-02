<template>
  <div class="my-exam-detail-page" v-loading="loading">
    <!-- 顶部导航 -->
    <div class="page-header">
      <el-button @click="$router.push('/my-exams')">← 返回考试列表</el-button>
    </div>

    <!-- 考试信息 -->
    <div class="exam-info-bar" v-if="examInfo">
      <span class="info-item">
        <el-icon><Calendar /></el-icon>
        {{ examInfo.title }}
      </span>
      <span class="info-item">
        <el-icon><Clock /></el-icon>
        {{ examInfo.exam_date }} {{ examInfo.start_time }} - {{ examInfo.end_time }}
      </span>
      <span class="info-item">总分：{{ examInfo.total_score }} 分</span>
      <span class="info-item">难度：{{ examInfo.difficulty?.toFixed(2) }}</span>
    </div>

    <!-- 题目列表 -->
    <div v-if="questions.length > 0">
      <div v-for="(q, index) in questions" :key="q.question_id" class="question-block">
        <div class="question-block-header">
          <el-tag type="primary" size="small">第{{ index + 1 }}题</el-tag>
          <el-tag size="small" type="warning" style="margin-left: 4px">
            难度: {{ q.difficulty?.toFixed(1) }}
          </el-tag>
          <el-tag size="small" type="success" style="margin-left: 4px">
            {{ q.max_score }}分
          </el-tag>
          <span class="q-title">{{ q.question_title || '-' }}</span>
        </div>

        <div class="question-split-view">
          <!-- 左栏：题干 -->
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

          <!-- 右栏：答案 -->
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

        <!-- 成绩显示 -->
        <div v-if="hasScores && studentScores[q.question_id] !== undefined" class="score-display">
          <el-tag type="success" size="small">得分：{{ studentScores[q.question_id] }} / {{ q.max_score }}</el-tag>
        </div>
      </div>
    </div>

    <el-empty v-else description="暂无题目" />

    <!-- PDF 查看区域 -->
    <div v-if="canViewPdf" class="pdf-section">
      <el-divider />
      <div class="pdf-header">
        <h3>试卷PDF</h3>
        <el-button type="primary" @click="generatePdf" :loading="generatingPdf" v-if="!pdfUrl">
          生成PDF
        </el-button>
      </div>
      <div v-if="pdfUrl" class="pdf-viewer-container">
        <iframe :src="pdfUrl" class="pdf-viewer" frameborder="0"></iframe>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../utils/api'
import katex from 'katex'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const examInfo = ref(null)
const questions = ref([])
const studentScores = ref({})
const hasScores = ref(false)
const canViewPdf = ref(false)
const pdfUrl = ref('')
const generatingPdf = ref(false)

// LaTeX渲染
function renderLatex(content) {
  if (!content) return ''
  try {
    const placeholders = []
    const hold = (html) => {
      const key = `\u0000KATEX${placeholders.length}\u0000`
      placeholders.push(html)
      return key
    }
    content = content.replace(/\$\$([\s\S]+?)\$\$/g, (match, latex) => {
      try { return hold(katex.renderToString(latex, { throwOnError: false, displayMode: true })) } catch { return match }
    })
    content = content.replace(/\$([^$\n]+?)\$/g, (match, latex) => {
      try { return hold(katex.renderToString(latex, { throwOnError: false })) } catch { return match }
    })
    placeholders.forEach((html, i) => {
      content = content.split(`\u0000KATEX${i}\u0000`).join(html)
    })
    return content
  } catch { return content }
}

// 获取图片URL
function getFullImageUrl(filename) {
  if (!filename) return ''
  if (filename.startsWith('http://') || filename.startsWith('https://')) return filename
  if (filename.startsWith('/')) return filename
  return `/api/questions/images/${filename}`
}

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
      return { url: getFullImageUrl(filename), sizeClass: getImageSizeClass(size) }
    }).filter(item => item.url)
  } catch { return [] }
}

function getAnswerImages(q) {
  if (!q.answer_images) return []
  try {
    const imgs = typeof q.answer_images === 'string' ? JSON.parse(q.answer_images) : q.answer_images
    if (!Array.isArray(imgs)) return []
    return imgs.map(item => {
      const filename = typeof item === 'string' ? item : (item.filename || '')
      const size = typeof item === 'object' && item.size ? item.size : 'medium'
      return { url: getFullImageUrl(filename), sizeClass: getImageSizeClass(size) }
    }).filter(item => item.url)
  } catch { return [] }
}

// 生成PDF
async function generatePdf() {
  generatingPdf.value = true
  try {
    const res = await api.get(`/papers/${examInfo.value.id}/export`)
    pdfUrl.value = res.pdf_url
    ElMessage.success('PDF生成成功')
  } catch {
    ElMessage.error('PDF生成失败')
  } finally {
    generatingPdf.value = false
  }
}

async function loadDetail() {
  loading.value = true
  try {
    const publishId = route.params.publishId
    const res = await api.get(`/papers/my-exams/${publishId}`)
    examInfo.value = res.paper
    questions.value = res.questions
    studentScores.value = res.student_scores || {}
    hasScores.value = res.has_scores
    canViewPdf.value = res.can_view
  } catch {
    ElMessage.error('加载考试详情失败')
    router.push('/my-exams')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadDetail()
})
</script>

<style scoped>
.my-exam-detail-page {
  padding: 20px;
}

.page-header {
  margin-bottom: 16px;
}

.exam-info-bar {
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

.score-display {
  padding: 8px 16px;
  background: #f0f9ff;
  border-top: 1px solid #ebeef5;
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

:deep(.image-size-large) { width: 90%; }
:deep(.image-size-medium) { width: 45%; }
:deep(.image-size-small) { width: 30%; }

.pdf-section {
  margin-top: 20px;
}

.pdf-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.pdf-header h3 {
  margin: 0;
  font-size: 16px;
}

.pdf-viewer-container {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  overflow: hidden;
}

.pdf-viewer {
  width: 100%;
  height: 800px;
  border: none;
}
</style>
