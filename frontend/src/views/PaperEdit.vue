<template>
  <div class="paper-edit-page">
    <el-row :gutter="20">
      <!-- 左侧：题目选择 -->
      <el-col :span="14">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>选择题目</span>
              <el-input
                v-model="searchKeyword"
                placeholder="搜索题目"
                style="width: 200px"
                clearable
                @keyup.enter="searchQuestions"
              >
                <template #append>
                  <el-button @click="searchQuestions">搜索</el-button>
                </template>
              </el-input>
            </div>
          </template>
          
          <!-- 筛选 -->
          <el-form :inline="true" size="small" style="margin-bottom: 15px">
            <el-form-item label="题型">
              <el-select v-model="filters.question_type" placeholder="全部" clearable @change="searchQuestions">
                <el-option label="理论题" value="theory" />
                <el-option label="实验理论题" value="experiment" />
              </el-select>
            </el-form-item>
            
            <el-form-item label="难度">
              <el-select v-model="filters.difficulty" placeholder="全部" clearable @change="searchQuestions">
                <el-option label="预赛难度" value="preliminary" />
                <el-option label="复赛难度" value="semi_final" />
                <el-option label="决赛难度" value="final" />
                <el-option label="CPhO难度" value="cpho" />
                <el-option label="IPhO难度" value="ipho" />
              </el-select>
            </el-form-item>
          </el-form>
          
          <!-- 题目列表 -->
          <div class="question-list" v-loading="loading">
            <div
              v-for="question in questions"
              :key="question.id"
              class="question-item"
              :class="{ selected: isSelected(question.id) }"
              @click="toggleQuestion(question)"
            >
              <div class="question-info">
                <el-tag size="small" :type="questionTypeTag(question.question_type)">
                  {{ questionTypeLabel(question.question_type) }}
                </el-tag>
                <el-tag size="small" :type="difficultyTag(question.difficulty)" style="margin-left: 5px">
                  {{ difficultyLabel(question.difficulty) }}
                </el-tag>
                <span class="question-id">ID: {{ question.id }}</span>
              </div>
              <div class="question-content" v-html="truncateContent(question.content)"></div>
              <div class="question-footer">
                <el-icon v-if="isSelected(question.id)" color="#409EFF"><Select /></el-icon>
              </div>
            </div>
          </div>
          
          <div class="pagination">
            <el-pagination
              v-model:current-page="pagination.page"
              :total="pagination.total"
              :page-size="pagination.perPage"
              layout="prev, pager, next"
              @current-change="loadQuestions"
            />
          </div>
        </el-card>
      </el-col>
      
      <!-- 右侧：试卷设置和已选题目 -->
      <el-col :span="10">
        <el-card>
          <template #header>
            <span>{{ isEdit ? '编辑试卷' : '新建试卷' }}</span>
          </template>
          
          <el-form :model="form" :rules="rules" ref="formRef" label-width="80px">
            <el-form-item label="试卷标题" prop="title">
              <el-input v-model="form.title" placeholder="请输入试卷标题" />
            </el-form-item>
            
            <el-form-item label="考试日期">
              <el-date-picker
                v-model="form.exam_date"
                type="date"
                placeholder="选择日期"
                value-format="YYYY-MM-DD"
                style="width: 100%"
              />
            </el-form-item>
            
            <el-form-item label="考试时长">
              <el-input-number v-model="form.duration" :min="30" :max="300" :step="15" />
              <span style="margin-left: 10px">分钟（默认180分钟）</span>
            </el-form-item>
            
            <el-divider />
            
            <div class="selected-header">
              <span>已选题目 ({{ selectedQuestions.length }}道)</span>
              <span>总分: {{ totalScore }}分</span>
            </div>
            
            <div class="selected-list">
              <div v-for="(item, index) in selectedQuestions" :key="item.question.id" class="selected-item">
                <div class="selected-info">
                  <span class="selected-index">第{{ index + 1 }}题</span>
                  <el-tag size="small">{{ questionTypeLabel(item.question.question_type) }}</el-tag>
                </div>
                <div class="selected-score">
                  <el-input-number
                    v-model="item.score"
                    :min="1"
                    :max="100"
                    size="small"
                    style="width: 80px"
                  />
                  <span style="margin-left: 5px">分</span>
                </div>
                <el-button type="danger" link @click="removeQuestion(index)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </div>
              
              <el-empty v-if="selectedQuestions.length === 0" description="请从左侧选择题目" />
            </div>
            
            <el-divider />
            
            <el-form-item>
              <el-button type="primary" @click="handleSubmit" :loading="submitting" :disabled="selectedQuestions.length === 0">
                {{ isEdit ? '保存修改' : '创建试卷' }}
              </el-button>
              <el-button @click="$router.back()">取消</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../utils/api'

const route = useRoute()
const router = useRouter()

const formRef = ref()
const loading = ref(false)
const submitting = ref(false)
const questions = ref([])
const selectedQuestions = ref([])
const searchKeyword = ref('')

const filters = reactive({
  question_type: '',
  difficulty: ''
})

const pagination = reactive({
  page: 1,
  perPage: 10,
  total: 0
})

const isEdit = computed(() => !!route.params.id)

const form = reactive({
  title: '',
  exam_date: '',
  duration: 180
})

const rules = {
  title: [{ required: true, message: '请输入试卷标题', trigger: 'blur' }]
}

const totalScore = computed(() => {
  return selectedQuestions.value.reduce((sum, item) => sum + item.score, 0)
})

function isSelected(questionId) {
  return selectedQuestions.value.some(item => item.question.id === questionId)
}

function toggleQuestion(question) {
  const index = selectedQuestions.value.findIndex(item => item.question.id === question.id)
  if (index > -1) {
    selectedQuestions.value.splice(index, 1)
  } else {
    // 使用题目的分值
    selectedQuestions.value.push({
      question,
      score: question.default_score || 10
    })
  }
}

function removeQuestion(index) {
  selectedQuestions.value.splice(index, 1)
}

async function loadQuestions() {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      per_page: pagination.perPage,
      keyword: searchKeyword.value,
      ...filters
    }
    
    Object.keys(params).forEach(key => {
      if (params[key] === '' || params[key] === null) {
        delete params[key]
      }
    })
    
    const res = await api.get('/questions', { params })
    questions.value = res.questions
    pagination.total = res.total
  } catch (error) {
    // 错误已处理
  } finally {
    loading.value = false
  }
}

function searchQuestions() {
  pagination.page = 1
  loadQuestions()
}

async function loadPaper() {
  if (!isEdit.value) return
  
  // 尝试从 sessionStorage 加载试卷数据（题库页面跳转过来）
  const storedPaper = sessionStorage.getItem('editingPaper')
  if (storedPaper) {
    sessionStorage.removeItem('editingPaper')
    try {
      const paper = JSON.parse(storedPaper)
      form.title = paper.paper_name
      // 加载试卷内的题目作为已选题目
      if (paper.questions) {
        selectedQuestions.value = paper.questions.map(q => ({
          question: q,
          score: q.default_score || 40
        }))
      }
      return
    } catch (e) {
      // 解析失败，走 API 加载
    }
  }
  
  // API 加载
  try {
    const res = await api.get(`/papers/${route.params.id}`)
    const paper = res.paper
    
    form.title = paper.title
    form.exam_date = paper.exam_date || ''
    form.duration = paper.duration || 180
    
    if (paper.questions) {
      selectedQuestions.value = paper.questions.map(item => ({
        question: item.question,
        score: item.score
      }))
    }
  } catch (error) {
    ElMessage.error('加载试卷失败')
    router.back()
  }
}

async function handleSubmit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  
  if (selectedQuestions.value.length === 0) {
    ElMessage.warning('请选择至少一道题目')
    return
  }
  
  submitting.value = true
  try {
    const data = {
      ...form,
      questions: selectedQuestions.value.map(item => ({
        question_id: item.question.id,
        score: item.score
      })),
      total_score: totalScore.value
    }
    
    if (isEdit.value) {
      await api.put(`/papers/${route.params.id}`, data)
      ElMessage.success('修改成功')
    } else {
      await api.post('/papers', data)
      ElMessage.success('创建成功')
    }
    
    router.push('/questions')
  } catch (error) {
    // 错误已处理
  } finally {
    submitting.value = false
  }
}

function truncateContent(content) {
  if (!content) return ''
  let text = content.replace(/\$\$?/g, '').replace(/\\[a-zA-Z]+/g, '')
  text = text.replace(/[{}]/g, '')
  return text.length > 80 ? text.substring(0, 80) + '...' : text
}

// 标签映射
const questionTypeMap = {
  choice: { label: '选择题', type: '' },
  fill: { label: '填空题', type: 'success' },
  calculation: { label: '计算题', type: 'warning' },
  experiment: { label: '实验题', type: 'info' },
  proof: { label: '证明题', type: 'danger' }
}

const difficultyMap = {
  preliminary: { label: '预赛', type: 'success' },
  semi_final: { label: '复赛', type: '' },
  final: { label: '决赛', type: 'warning' },
  cpho: { label: 'CPhO', type: 'danger' },
  ipho: { label: 'IPhO', type: 'danger' }
}

const questionTypeLabel = (type) => questionTypeMap[type]?.label || type
const questionTypeTag = (type) => questionTypeMap[type]?.type || ''
const difficultyLabel = (d) => difficultyMap[d]?.label || d
const difficultyTag = (d) => difficultyMap[d]?.type || ''

onMounted(() => {
  loadQuestions()
  loadPaper()
})
</script>

<style scoped>
.paper-edit-page {
  height: calc(100vh - 120px);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.question-list {
  max-height: 500px;
  overflow-y: auto;
}

.question-item {
  padding: 12px;
  margin-bottom: 10px;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s;
}

.question-item:hover {
  border-color: #409EFF;
}

.question-item.selected {
  border-color: #409EFF;
  background: #ecf5ff;
}

.question-info {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}

.question-id {
  margin-left: auto;
  font-size: 12px;
  color: #909399;
}

.question-content {
  font-size: 13px;
  color: #606266;
  line-height: 1.5;
}

.question-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
}

.pagination {
  margin-top: 15px;
  display: flex;
  justify-content: center;
}

.selected-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 15px;
  font-weight: 500;
}

.selected-list {
  max-height: 300px;
  overflow-y: auto;
}

.selected-item {
  display: flex;
  align-items: center;
  padding: 10px;
  margin-bottom: 8px;
  background: #f5f7fa;
  border-radius: 4px;
}

.selected-info {
  flex: 1;
  display: flex;
  align-items: center;
}

.selected-index {
  font-weight: 500;
  margin-right: 10px;
}

.selected-score {
  display: flex;
  align-items: center;
  margin-right: 15px;
}
</style>
