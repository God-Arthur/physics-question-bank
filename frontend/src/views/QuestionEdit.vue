<template>
  <div class="question-edit-page">
    <el-card>
      <template #header>
        <span>{{ isEdit ? '编辑题目' : '添加题目' }}</span>
      </template>
      
      <el-form :model="form" :rules="rules" ref="formRef" label-width="80px" hide-required-asterisk>
        <!-- 第一行：题型、难度、分值、年份、作者 -->
        <el-row :gutter="16">
          <el-col :span="5">
            <el-form-item label="题型" prop="question_type">
              <el-select v-model="form.question_type" placeholder="请选择题型">
                <el-option label="理论题" value="theory" />
                <el-option label="实验理论题" value="experiment" />
              </el-select>
            </el-form-item>
          </el-col>

          <el-col :span="4">
            <el-form-item label="难度" prop="difficulty">
              <el-input v-model="difficultyStr" placeholder="0.0~5.0" @input="onDifficultyInput" @blur="onDifficultyBlur" />
            </el-form-item>
          </el-col>

          <el-col :span="4">
            <el-form-item label="分值" prop="default_score">
              <el-input v-model="scoreStr" placeholder="分值" @input="onScoreInput" @blur="onScoreBlur" />
            </el-form-item>
          </el-col>

          <el-col :span="4">
            <el-form-item label="年份" prop="year">
              <el-input v-model="yearStr" placeholder="年份" @input="onYearInput" @blur="onYearBlur" />
            </el-form-item>
          </el-col>

          <el-col :span="7">
            <el-form-item label="作者">
              <el-input v-model="form.author" placeholder="请输入作者姓名" />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 第二行：题目标题 -->
        <el-form-item label="题目标题" prop="question_title">
          <el-input v-model="form.question_title" placeholder="请输入题目标题" />
        </el-form-item>

        <!-- 第三行：来源类型和机构 -->
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="来源类型" prop="source_type">
              <el-select v-model="form.source_type" placeholder="请选择来源" @change="handleSourceTypeChange">
                <el-option label="历年真题" value="past_exam" />
                <el-option label="模拟题" value="mock" />
              </el-select>
            </el-form-item>
          </el-col>

          <el-col :span="8" v-if="form.source_type === 'mock'">
            <el-form-item label="出题机构">
              <el-select 
                v-model="form.source_institute" 
                placeholder="请选择机构" 
                style="width: 100%"
                @change="handleInstituteChange"
              >
                <el-option 
                  v-for="inst in instituteList" 
                  :key="inst.code"
                  :label="inst.name" 
                  :value="inst.code" 
                />
                <el-divider style="margin: 4px 0" />
                <el-option label="个人" value="IND" />
                <el-divider style="margin: 4px 0" />
                <el-option label="编辑" value="__EDIT__">
                  <span style="color: #409eff">编辑</span>
                </el-option>
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-form-item label="题干内容" prop="content">
          <div class="editor-container">
            <el-input
              v-model="form.content"
              type="textarea"
              :rows="8"
              placeholder="请输入题干内容，支持LaTeX公式（使用$...$包裹）"
            />
            <div class="preview-section">
              <div class="preview-label">预览：</div>
              <div class="preview-content latex-content" v-html="renderLatex(form.content)"></div>
            </div>
          </div>
        </el-form-item>
        
        <el-form-item label="题干图片">
          <el-upload
            :action="uploadUrl"
            :headers="uploadHeaders"
            :data="uploadData"
            :on-success="handleContentImageSuccess"
            :show-file-list="false"
            accept="image/*"
          >
            <el-button type="primary">上传图片</el-button>
          </el-upload>
          <div class="image-list" v-if="form.content_images.length">
            <div v-for="(img, index) in form.content_images" :key="index" class="image-item">
              <el-image
                :src="getImageUrl(img.filename)"
                fit="contain"
                style="width: 100px; height: 80px"
              >
                <template #error>
                  <div class="image-error">加载失败</div>
                </template>
              </el-image>
              <div class="image-actions">
                <el-select v-model="img.size" size="small" style="width: 90px">
                  <el-option label="大" value="large" />
                  <el-option label="中" value="medium" />
                  <el-option label="小" value="small" />
                </el-select>
                <el-button type="danger" size="small" circle @click="removeContentImage(index)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </div>
            </div>
          </div>
        </el-form-item>
        
        <el-form-item label="答案内容" prop="answer">
          <div class="editor-container">
            <el-input
              v-model="form.answer"
              type="textarea"
              :rows="8"
              placeholder="请输入答案内容，支持LaTeX公式"
            />
            <div class="preview-section">
              <div class="preview-label">预览：</div>
              <div class="preview-content latex-content" v-html="renderLatex(form.answer)"></div>
            </div>
          </div>
        </el-form-item>
        
        <el-form-item label="答案图片">
          <el-upload
            :action="uploadUrl"
            :headers="uploadHeaders"
            :data="uploadData"
            :on-success="handleAnswerImageSuccess"
            :show-file-list="false"
            accept="image/*"
          >
            <el-button type="primary">上传图片</el-button>
          </el-upload>
          <div class="image-list" v-if="form.answer_images.length">
            <div v-for="(img, index) in form.answer_images" :key="index" class="image-item">
              <el-image
                :src="getImageUrl(img.filename)"
                fit="contain"
                style="width: 100px; height: 80px"
              />
              <div class="image-actions">
                <el-select v-model="img.size" size="small" style="width: 90px">
                  <el-option label="大" value="large" />
                  <el-option label="中" value="medium" />
                  <el-option label="小" value="small" />
                </el-select>
                <el-button type="danger" size="small" circle @click="removeAnswerImage(index)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </div>
            </div>
          </div>
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" @click="handleSubmit" :loading="loading">
            {{ isEdit ? '保存修改' : '提交题目' }}
          </el-button>
          <el-button @click="$router.back()">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>
    
    <!-- 添加机构对话框 -->
    <el-dialog v-model="addInstituteDialogVisible" title="添加机构" width="400px">
      <el-form :model="instituteForm" :rules="instituteRules" ref="instituteFormRef" label-width="90px">
        <el-form-item label="机构名称" prop="name">
          <el-input v-model="instituteForm.name" placeholder="如：兰阶" />
        </el-form-item>
        <el-form-item label="机构代码" prop="code">
          <el-input v-model="instituteForm.code" placeholder="3位大写字母" maxlength="3" style="text-transform: uppercase" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addInstituteDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitAddInstitute" :loading="instituteSubmitting">确定</el-button>
      </template>
    </el-dialog>

    <!-- 机构管理弹窗 -->
    <el-dialog v-model="manageInstituteDialogVisible" title="机构管理" width="600px" :close-on-click-modal="false" :show-close="false">
      <div style="margin-bottom: 15px">
        <el-button type="primary" size="small" @click="openAddInstituteInManage">添加机构</el-button>
      </div>

      <el-table :data="[...instituteList.filter(i => i.code !== 'IND'), ...instituteList.filter(i => i.code === 'IND')]" size="small" border>
        <el-table-column prop="code" label="代码" width="100">
          <template #default="{ row }">
            <span :style="row.code === 'IND' ? 'color: #909399' : ''">{{ row.code }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="名称">
          <template #default="{ row }">
            <span :style="row.code === 'IND' ? 'color: #909399' : ''">{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button
              v-if="!defaultInstituteCodes.includes(row.code)"
              type="primary"
              link
              size="small"
              @click="editInstitute(row)"
            >
              编辑
            </el-button>
            <el-button
              v-if="!defaultInstituteCodes.includes(row.code)"
              type="danger"
              link
              size="small"
              @click="deleteInstitute(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-divider v-if="manageInstituteMode !== 'view'" />

      <el-form v-if="manageInstituteMode !== 'view'" :model="manageInstituteForm" :rules="instituteRules" ref="manageInstituteFormRef" label-width="90px" hide-required-asterisk>
        <el-form-item label="机构名称" prop="name">
          <el-input v-model="manageInstituteForm.name" placeholder="如：兰阶" />
        </el-form-item>
        <el-form-item label="机构代码" prop="code">
          <el-input
            v-model="manageInstituteForm.code"
            placeholder="3位大写字母"
            maxlength="3"
            style="text-transform: uppercase"
            :disabled="manageInstituteMode === 'edit'"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="manageInstituteDialogVisible = false">{{ manageInstituteMode === 'view' ? '关闭' : '取消' }}</el-button>
        <el-button v-if="manageInstituteMode !== 'view'" type="primary" @click="submitManageInstitute" :loading="manageInstituteSubmitting">
          {{ manageInstituteMode === 'add' ? '添加' : '保存' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter, onBeforeRouteLeave } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete } from '@element-plus/icons-vue'
import api from '../utils/api'
import { useAuthStore } from '../stores/auth'
import { ensureUploadSession, cleanupUploadSessionAuth, cleanupUploadSessionNoAuth } from '../utils/uploadSession'
import { renderLatex } from '../utils/latex'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const formRef = ref()
const loading = ref(false)
const instituteList = ref([])

// 添加机构对话框
const addInstituteDialogVisible = ref(false)
const instituteSubmitting = ref(false)
const instituteFormRef = ref(null)
const instituteForm = reactive({
  name: '',
  code: ''
})
const instituteRules = {
  name: [{ required: true, message: '请输入机构名称', trigger: 'blur' }],
  code: [
    { required: true, message: '请输入机构代码', trigger: 'blur' },
    { pattern: /^[A-Z]{3}$/, message: '必须是3位大写字母', trigger: 'blur' }
  ]
}

// 机构管理弹窗
const manageInstituteDialogVisible = ref(false)
const manageInstituteMode = ref('view') // 'view' | 'add' | 'edit'
const manageInstituteSubmitting = ref(false)
const manageInstituteFormRef = ref(null)
const manageInstituteForm = reactive({
  id: null,
  name: '',
  code: ''
})
const defaultInstituteCodes = ['AJZ', 'BOZ', 'FYU', 'LAN', 'PJI', 'PKU', 'QUA', 'SBO', 'THU', 'WMS', 'XES', 'XYZ', 'YFD', 'ZHM', 'ZHX', 'IND', 'NUL']

const isEdit = computed(() => !!route.params.id)

const form = reactive({
  question_type: 'theory',
  difficulty: 3.0,
  source_type: '',
  source_institute: '',
  author: '',
  year: new Date().getFullYear(),
  default_score: 40,
  question_title: '',
  content: '',
  content_images: [],
  answer: '',
  answer_images: []
})

// 年份、分值和难度的字符串表示（用于输入框）
const yearStr = ref(String(form.year))
const scoreStr = ref(String(form.default_score))
const difficultyStr = ref(String(form.difficulty))

// 难度输入处理（允许 0.1 ~ 5.0，保留一位小数）
function onDifficultyInput(val) {
  const cleaned = val.replace(/[^\d.]/g, '')
  const parts = cleaned.split('.')
  const limited = parts.length > 2 ? parts[0] + '.' + parts.slice(1).join('') : cleaned
  difficultyStr.value = limited
}

function onDifficultyBlur() {
  const parsed = parseFloat(difficultyStr.value)
  if (isNaN(parsed) || parsed < 0.1) {
    difficultyStr.value = ''
    form.difficulty = null
  } else {
    const clamped = Math.min(5.0, Math.max(0.1, parsed))
    const rounded = Math.round(clamped * 10) / 10
    difficultyStr.value = String(rounded)
    form.difficulty = rounded
  }
}

// 年份输入处理（只允许正整数，1900-2100）
function onYearInput(val) {
  const cleaned = val.replace(/[^\d]/g, '').slice(0, 4)
  yearStr.value = cleaned
  form.year = cleaned ? parseInt(cleaned, 10) : null
}

function onYearBlur() {
  if (!yearStr.value) {
    const currentYear = new Date().getFullYear()
    yearStr.value = String(currentYear)
    form.year = currentYear
    return
  }
  const y = parseInt(yearStr.value, 10)
  if (y < 1900) {
    yearStr.value = '1900'
    form.year = 1900
  } else if (y > 2100) {
    yearStr.value = '2100'
    form.year = 2100
  }
}

// 分值输入处理（只允许正整数）
function onScoreInput(val) {
  const cleaned = val.replace(/[^\d]/g, '').slice(0, 3)
  scoreStr.value = cleaned
  form.default_score = cleaned ? parseInt(cleaned, 10) : null
}

function onScoreBlur() {
  if (!scoreStr.value || parseInt(scoreStr.value, 10) <= 0) {
    scoreStr.value = '40'
    form.default_score = 40
  }
}

const rules = {
  question_type: [{ required: true, message: '请选择题型', trigger: 'change' }],
  difficulty: [{ required: true, message: '请设置难度', trigger: 'blur' }],
  default_score: [{ required: true, message: '请设置分值', trigger: 'blur' }],
  year: [{ required: true, message: '请设置年份', trigger: 'blur' }],
  source_type: [{ required: true, message: '请选择来源类型', trigger: 'change' }],
  question_title: [{ required: true, message: '请输入题目标题', trigger: 'blur' }],
  content: [{ required: true, message: '请输入题干内容', trigger: 'blur' }],
  answer: [{ required: true, message: '请输入答案内容', trigger: 'blur' }]
}

const uploadUrl = '/api/questions/upload'
const uploadHeaders = computed(() => ({
  Authorization: `Bearer ${authStore.token}`
}))

// 上传会话：用于暂存上传的图片，便于在取消/超时/登出时精确清理
const uploadSession = ref(null)
const uploadSessionId = computed(() => uploadSession.value?.session_id || '')
const uploadData = computed(() => uploadSessionId.value ? ({ session_id: uploadSessionId.value }) : ({}))

async function ensureSessionReady() {
  if (uploadSession.value) return uploadSession.value
  uploadSession.value = await ensureUploadSession(api)
  return uploadSession.value
}

async function cleanupCurrentSession() {
  if (!uploadSession.value) return
  try {
    await cleanupUploadSessionAuth(api)
  } finally {
    uploadSession.value = null
  }
}

async function loadInstitutes() {
  try {
    const res = await api.get('/institutes/')
    instituteList.value = res.institutes || []
  } catch (error) {
    // 错误已处理
  }
}

async function loadQuestion() {
  if (!isEdit.value) return
  
  try {
    const res = await api.get(`/questions/${route.params.id}`)
    const q = res.question
    
    form.question_type = q.question_type
    form.difficulty = q.difficulty
    form.source_type = q.source_type || ''
    form.source_institute = q.source_institute || ''
    form.author = q.author || ''
    form.year = q.year || new Date().getFullYear()
    form.default_score = q.default_score || 40
    form.question_title = q.question_title || ''
    form.content = q.content
    form.answer = q.answer
    
    // 同步字符串值
    yearStr.value = String(form.year)
    scoreStr.value = String(form.default_score)
    difficultyStr.value = String(form.difficulty)
    
    // 解析图片
    if (q.content_images) {
      try {
        form.content_images = normalizeImageList(JSON.parse(q.content_images))
      } catch {
        form.content_images = []
      }
    }
    if (q.answer_images) {
      try {
        form.answer_images = normalizeImageList(JSON.parse(q.answer_images))
      } catch {
        form.answer_images = []
      }
    }
  } catch (error) {
    ElMessage.error('加载题目失败')
    router.back()
  }
}

// 兼容旧数据：将字符串数组转换为 {filename, size} 对象数组
function normalizeImageList(list) {
  if (!Array.isArray(list)) return []
  return list.map(item => {
    if (typeof item === 'string') {
      return { filename: item, size: 'medium' }
    }
    return { filename: item.filename || '', size: item.size || 'medium' }
  }).filter(item => item.filename)
}

// 获取图片URL（兼容字符串和对象格式）
function getImageUrl(img) {
  if (!img) return ''
  const filename = typeof img === 'string' ? img : (img.filename || '')
  if (!filename) return ''
  return `/api/questions/images/${filename}`
}

function handleContentImageSuccess(response) {
  if (response.filename) {
    form.content_images.push({ filename: response.filename, size: 'medium' })
  }
}

function handleAnswerImageSuccess(response) {
  if (response.filename) {
    form.answer_images.push({ filename: response.filename, size: 'medium' })
  }
}

function removeContentImage(index) {
  form.content_images.splice(index, 1)
}

function removeAnswerImage(index) {
  form.answer_images.splice(index, 1)
}

function handleSourceTypeChange(val) {
  // 切换来源类型时清空相关字段
  if (val !== 'mock') {
    form.source_institute = ''
  }
  if (val !== 'original') {
    form.author = ''
  }
}

function handleInstituteChange(val) {
  if (val === '__EDIT__') {
    // 打开机构管理弹窗（查看模式）
    manageInstituteMode.value = 'view'
    manageInstituteDialogVisible.value = true
    // 重置选择
    form.source_institute = ''
  }
}

function showAddInstituteDialog() {
  instituteForm.name = ''
  instituteForm.code = ''
  addInstituteDialogVisible.value = true
}

async function submitAddInstitute() {
  if (!instituteFormRef.value) return
  await instituteFormRef.value.validate(async (valid) => {
    if (!valid) return
    instituteSubmitting.value = true
    try {
      const res = await api.post('/institutes/', {
        name: instituteForm.name,
        code: instituteForm.code.toUpperCase()
      })
      ElMessage.success(`机构 ${res.institute.code} 创建成功`)
      // 自动选中新创建的机构
      form.source_institute = res.institute.code
      addInstituteDialogVisible.value = false
      // 刷新机构列表
      await loadInstitutes()
    } catch (error) {
      // 错误已处理
    } finally {
      instituteSubmitting.value = false
    }
  })
}

// 打开机构管理弹窗
function openManageInstituteDialog() {
  manageInstituteMode.value = 'view'
  manageInstituteDialogVisible.value = true
}

// 添加机构（在管理弹窗内）
function openAddInstituteInManage() {
  manageInstituteMode.value = 'add'
  manageInstituteForm.id = null
  manageInstituteForm.name = ''
  manageInstituteForm.code = ''
}

// 编辑机构
function editInstitute(row) {
  manageInstituteMode.value = 'edit'
  manageInstituteForm.id = row.id
  manageInstituteForm.name = row.name
  manageInstituteForm.code = row.code
}

// 提交机构管理（添加/编辑）
async function submitManageInstitute() {
  if (!manageInstituteFormRef.value) return
  await manageInstituteFormRef.value.validate(async (valid) => {
    if (!valid) return
    manageInstituteSubmitting.value = true
    try {
      if (manageInstituteMode.value === 'add') {
        const res = await api.post('/institutes/', {
          name: manageInstituteForm.name,
          code: manageInstituteForm.code.toUpperCase()
        })
        ElMessage.success(`机构 ${res.institute.code} 创建成功`)
      } else if (manageInstituteMode.value === 'edit') {
        const res = await api.put(`/institutes/${manageInstituteForm.id}`, {
          name: manageInstituteForm.name
        })
        ElMessage.success(`机构 ${res.institute.code} 更新成功`)
      }
      manageInstituteMode.value = 'view'
      await loadInstitutes()
    } catch (error) {
      // 错误已处理
    } finally {
      manageInstituteSubmitting.value = false
    }
  })
}

// 删除机构
async function deleteInstitute(row) {
  try {
    await ElMessageBox.confirm(
      `确定要删除机构 ${row.name} (${row.code}) 吗？`,
      '确认删除',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
    await api.delete(`/institutes/${row.id}`)
    ElMessage.success('删除成功')
    await loadInstitutes()
  } catch (error) {
    if (error !== 'cancel') {
      // 错误已处理
    }
  }
}

async function handleSubmit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  
  loading.value = true
  try {
    // 确保上传会话已创建（如果有图片需要迁移）
    if (form.content_images.length > 0 || form.answer_images.length > 0) {
      await ensureSessionReady()
    }
    
    const data = {
      ...form,
      content_images: form.content_images,
      answer_images: form.answer_images
    }
    
    // 如果有上传会话，传递 session_id 给后端用于图片迁移
    if (uploadSessionId.value) {
      data.upload_session_id = uploadSessionId.value
    }
    
    if (isEdit.value) {
      await api.put(`/questions/${route.params.id}`, data)
      ElMessage.success('修改成功')
    } else {
      await api.post('/questions', data)
      ElMessage.success('提交成功')
    }
    
    // 提交成功后清理上传会话（后端已做迁移+清理）
    await cleanupCurrentSession()
    
    // 如果有来源页（试卷详情页），返回来源页
    const from = route.query.from
    if (from) {
      router.push(`/papers/${from}`)
    } else {
      router.push('/questions')
    }
  } catch (error) {
    // 错误已处理
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadInstitutes()
  loadQuestion()
})

// 跳转离开页面：视为取消创建，清理本次会话的临时文件
onBeforeRouteLeave(async () => {
  await cleanupCurrentSession()
})

onBeforeUnmount(async () => {
  await cleanupCurrentSession()
})

// 关闭标签页/刷新：尽力清理（不依赖 token）
function _onBeforeUnload() {
  cleanupUploadSessionNoAuth()
}
window.addEventListener('beforeunload', _onBeforeUnload)
onBeforeUnmount(() => window.removeEventListener('beforeunload', _onBeforeUnload))
</script>

<style scoped>
.question-edit-page {
  max-width: 1000px;
  margin: 0 auto;
}

.editor-container {
  width: 100%;
}

.preview-section {
  margin-top: 10px;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 4px;
  min-height: 60px;
}

.preview-label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 8px;
}

.preview-content {
  line-height: 1.8;
}

.image-list {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.image-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.image-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.image-error {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  height: 100%;
  background: #f5f7fa;
  color: #909399;
  font-size: 12px;
}
</style>
