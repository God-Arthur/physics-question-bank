<template>
  <div class="questions-page">
    <!-- 搜索筛选 -->
    <el-card class="filter-card">
      <el-form :model="filters" label-width="70px">
        <!-- 关键词搜索行 -->
        <div class="keyword-row">
          <el-input v-model="filters.keyword" placeholder="输入关键词" clearable @keyup.enter="handleSearch" style="flex: 1">
          </el-input>
          <el-button type="primary" @click="handleSearch" style="margin-left: 12px">搜索</el-button>
          <el-button link type="primary" @click="showAdvanced = !showAdvanced" style="margin-left: 8px">
            <el-icon><ArrowDown v-if="!showAdvanced" /><ArrowUp v-else /></el-icon>
            {{ showAdvanced ? '收起' : '高级' }}
          </el-button>
          <el-button link type="info" @click="resetFilters">重置</el-button>
        </div>
        
        <!-- 高级筛选 -->
        <div v-if="showAdvanced" class="advanced-filters">
          <el-divider style="margin: 12px 0" />
          
          <!-- 匹配范围占一行 -->
          <el-form-item label="匹配范围" class="filter-row">
            <el-checkbox-group v-model="filters.matchScope">
              <el-checkbox label="paper">匹配试卷</el-checkbox>
              <el-checkbox label="question">匹配题目</el-checkbox>
            </el-checkbox-group>
          </el-form-item>
          
          <!-- 题型、难度、年份占一行 -->
          <div class="filter-row multi-col">
            <el-form-item label="题型" class="inline-item">
              <el-select v-model="filters.question_type" placeholder="全部" clearable style="width: 120px">
                <el-option label="理论题" value="theory" />
                <el-option label="实验理论题" value="experiment" />
              </el-select>
            </el-form-item>
            
            <el-form-item label="难度" class="inline-item">
              <div class="difficulty-range">
                <el-input
                  v-model="difficultyMinStr"
                  placeholder="最低"
                  style="width: 70px"
                  @input="onDifficultyMinInput"
                  @blur="formatDifficulty('min')"
                />
                <span class="difficulty-sep">-</span>
                <el-input
                  v-model="difficultyMaxStr"
                  placeholder="最高"
                  style="width: 70px"
                  @input="onDifficultyMaxInput"
                  @blur="formatDifficulty('max')"
                />
              </div>
            </el-form-item>
            
            <el-form-item label="年份" class="inline-item">
              <el-input
                v-model="yearStr"
                placeholder="全部"
                clearable
                style="width: 100px"
                @input="onYearInput"
              />
            </el-form-item>
          </div>
          
          <!-- 来源占一行 -->
          <div class="filter-row">
            <el-form-item label="来源" class="inline-item">
              <el-select v-model="filters.source_type" placeholder="全部" clearable style="width: 140px" @change="handleSourceTypeChange">
                <el-option label="历年真题" value="past_exam" />
                <el-option label="模拟题" value="mock" />
              </el-select>
            </el-form-item>
            
            <!-- 模拟题显示机构筛选 -->
            <el-form-item v-if="filters.source_type === 'mock'" class="inline-item" style="margin-left: 16px">
              <div style="display: flex; align-items: center; gap: 8px">
                <el-select v-model="filters.source_institute" placeholder="选择机构" clearable style="width: 160px" filterable>
                  <el-option v-for="inst in instituteList" :key="inst.code" :label="`${inst.name} (${inst.code})`" :value="inst.code" />
                </el-select>
                <el-button type="primary" link @click="showAddInstituteDialog" style="padding: 0">
                  <el-icon><Plus /></el-icon>
                  添加机构
                </el-button>
              </div>
            </el-form-item>
            
            <!-- 原创题显示作者筛选 -->
            <el-form-item v-if="filters.source_type === 'original'" class="inline-item" style="margin-left: 16px">
              <el-input v-model="filters.author" placeholder="请输入作者" clearable style="width: 140px" />
            </el-form-item>
          </div>
        </div>
      </el-form>
    </el-card>

    <!-- 操作栏 -->
    <div class="action-bar">
      <el-button type="primary" @click="$router.push('/questions/create')" v-if="canEdit">
        <el-icon><Plus /></el-icon>
        添加题目
      </el-button>
      <el-button type="success" @click="$router.push('/import')" v-if="canEdit">
        <el-icon><Upload /></el-icon>
        批量导入
      </el-button>
      <el-button 
        :type="composeMode ? 'warning' : 'info'" 
        plain 
        @click="toggleComposeMode"
      >
        <el-icon><Document /></el-icon>
        {{ composeMode ? '退出组卷' : '组卷' }}
      </el-button>
      <el-button 
        v-if="!composeMode"
        type="danger" 
        :disabled="selectedPapers.length === 0" 
        @click="batchDeletePapers"
      >
        <el-icon><Delete /></el-icon>
        {{ selectedPapers.length <= 1 ? '删除' : `删除 (${selectedPapers.length})` }}
      </el-button>
      <el-button 
        v-if="composeMode"
        type="success" 
        :disabled="selectedQuestions.length === 0"
        @click="goToCompose"
      >
        <el-icon><DocumentChecked /></el-icon>
        新建试卷 ({{ selectedQuestions.length }})
      </el-button>
      <el-button type="info" plain @click="showDifficultyMap = !showDifficultyMap" style="margin-left: auto">
        难度映射表
      </el-button>
    </div>
    
    <!-- 难度映射表模块 -->
    <Transition name="expand">
      <div v-if="showDifficultyMap" class="difficulty-map-module">
        <div class="difficulty-map-header">
          <span class="difficulty-map-title">得分率 → 难度系数映射（逻辑斯蒂拟合）</span>
          <div>
            <el-tag v-if="difficultyMapping.need_fit" type="warning" size="small" style="margin-right: 8px">数据已更新，需要重新拟合</el-tag>
            <el-button type="primary" size="small" @click="fitDifficultyMapping" :loading="fitting">重新拟合</el-button>
          </div>
        </div>
        <el-table :data="difficultyMapping.mapping" stripe size="small" border v-if="difficultyMapping.mapping.length > 0">
          <el-table-column prop="score_rate" label="得分率" width="100" align="center">
            <template #default="{ row }">
              <span style="font-weight: bold">{{ row.score_rate }}%</span>
            </template>
          </el-table-column>
          <el-table-column prop="difficulty" label="难度系数" align="center">
            <template #default="{ row }">
              <span v-if="row.difficulty" style="font-size: 16px; color: #409EFF; font-weight: bold">{{ row.difficulty.toFixed(2) }}</span>
              <span v-else style="color: #909399">-</span>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-else description="暂无拟合数据，请点击重新拟合" />
        <div v-if="difficultyMapping.last_fitted_at" style="margin-top: 8px; font-size: 12px; color: #909399">
          上次拟合时间: {{ new Date(difficultyMapping.last_fitted_at).toLocaleString('zh-CN') }}
        </div>
      </div>
    </Transition>
    
    <!-- 试卷列表 -->
    <div v-loading="loading">
      <el-empty v-if="!loading && groups.length === 0" description="暂无数据" />
      
      <div v-else class="paper-list">
        <div 
          v-for="(group, index) in groups" 
          :key="index" 
          class="paper-item"
          @click="togglePaperExpand(index)"
        >
          <div class="paper-header">
            <el-checkbox 
              :model-value="selectedPapers.includes(group.paper_id)" 
              @click.stop
              @change="togglePaperSelection(group.paper_id)"
              style="margin-right: 8px"
            />
            <el-tag type="primary" size="small">{{ group.paper_id }}</el-tag>
            <el-icon style="color: #606266; margin: 0 6px"><Tickets /></el-icon>
            <span class="paper-name">{{ group.paper_name }}</span>
            <el-tag size="small" type="info" style="margin-left: 8px">{{ group.question_count }} 题</el-tag>
            <el-tag size="small" type="warning" style="margin-left: 4px">{{ group.difficulty?.toFixed(2) }}</el-tag>
            <el-button v-if="!composeMode" type="primary" link size="small" style="margin-left: 12px" @click.stop="editPaper(group)">查看</el-button>
            <el-icon class="expand-icon" :class="{ expanded: expandedPapers.includes(index) }">
              <ArrowDown />
            </el-icon>
          </div>
          
          <Transition name="expand">
            <div v-show="expandedPapers.includes(index)" class="paper-content" @click.stop>
              <el-table 
                :data="group.questions" 
                stripe 
                size="small" 
                :row-class-name="getQuestionRowClass"
                :ref="el => setTableRef(el, group.paper_id)"
                @selection-change="(selection) => handleQuestionSelectionChange(selection, group.paper_id)"
              >
                <el-table-column v-if="composeMode" type="selection" width="55" />
                <el-table-column label="题号" width="70">
                  <template #default="scope">
                    {{ scope.row.question_number }}
                  </template>
                </el-table-column>
                
                <el-table-column label="题目标题" min-width="180">
                  <template #default="scope">
                    {{ scope.row.question_title || '-' }}
                  </template>
                </el-table-column>
                
                <el-table-column label="题型" width="110">
                  <template #default="scope">
                    <el-tag :type="questionTypeTag(scope.row.question_type)" size="small">
                      {{ questionTypeLabel(scope.row.question_type) }}
                    </el-tag>
                  </template>
                </el-table-column>
                
                <el-table-column label="难度" width="80">
                  <template #default="scope">
                    {{ scope.row.difficulty?.toFixed(1) || '-' }}
                  </template>
                </el-table-column>
                
                <el-table-column label="来源" width="120">
                  <template #default="scope">
                    <el-tag size="small" type="info">
                      {{ sourceTypeLabel(scope.row.source_type) }}
                    </el-tag>
                  </template>
                </el-table-column>

                <el-table-column prop="use_count" label="使用次数" width="90" />
                
                <el-table-column label="操作" width="80" fixed="right">
                  <template #default="scope">
                    <el-button type="primary" link size="small" @click="viewQuestion(scope.row)">查看</el-button>
                  </template>
                </el-table-column>
              </el-table>
              
              <!-- 试卷详细信息 -->
              <div class="paper-summary">
                <span v-if="shouldShowInstitute(group)" class="summary-item">
                  <el-icon style="margin-right: 4px"><OfficeBuilding /></el-icon>
                  机构：{{ getPaperInstitute(group) }}
                </span>
                <span class="summary-item">
                  <el-icon style="margin-right: 4px"><Calendar /></el-icon>
                  年份：{{ getPaperYear(group) }}
                </span>
                <span class="summary-item">
                  <el-icon style="margin-right: 4px"><User /></el-icon>
                  作者：{{ getPaperAuthors(group) }}
                </span>
                <span class="summary-item">
                  总分：{{ getPaperTotalScore(group) }} 分
                </span>
              </div>
            </div>
          </Transition>
        </div>
      </div>
      
      <div class="pagination" style="margin-top: 20px">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.perPage"
          :total="pagination.total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @size-change="loadQuestions"
          @current-change="loadQuestions"
        />
      </div>
    </div>
    
    <!-- 查看题目对话框 -->
    <el-dialog v-model="viewDialogVisible" title="题目详情" width="900px" top="5vh">
      <template v-if="currentQuestion">
        <div class="question-meta">
          <el-tag size="small">{{ questionTypeLabel(currentQuestion.question_type) }}</el-tag>
          <el-tag size="small" type="warning" style="margin-left: 6px">难度: {{ currentQuestion.difficulty?.toFixed(1) }}</el-tag>
        </div>
        <div class="question-split-view">
          <div class="question-panel">
            <div class="panel-header">题干</div>
            <div class="panel-body">
              <div class="latex-content" v-html="renderLatex(currentQuestion.content)"></div>
              <div class="content-images" v-if="getContentImages(currentQuestion).length > 0">
                <el-image
                  v-for="(img, i) in getContentImages(currentQuestion)"
                  :key="i"
                  :src="img.url"
                  fit="contain"
                  :class="img.sizeClass"
                  style="margin-bottom: 8px; display: block"
                  :preview-src-list="getContentImages(currentQuestion).map(x => x.url)"
                />
              </div>
            </div>
          </div>
          <div class="answer-panel">
            <div class="panel-header">答案</div>
            <div class="panel-body">
              <div class="latex-content" v-html="renderLatex(currentQuestion.answer)"></div>
              <div class="content-images" v-if="getAnswerImages(currentQuestion).length > 0">
                <el-image
                  v-for="(img, i) in getAnswerImages(currentQuestion)"
                  :key="i"
                  :src="img.url"
                  fit="contain"
                  :class="img.sizeClass"
                  style="margin-bottom: 8px; display: block"
                  :preview-src-list="getAnswerImages(currentQuestion).map(x => x.url)"
                />
              </div>
            </div>
          </div>
        </div>
      </template>
    </el-dialog>
    
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
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../utils/api'
import { useAuthStore } from '../stores/auth'
import { renderLatex } from '../utils/latex'

const router = useRouter()
const authStore = useAuthStore()

const loading = ref(false)
const questions = ref([])
const groups = ref([])
const expandedPapers = ref([])
const matchedQuestionIds = ref(new Set()) // 存储匹配的题目ID
const selectedPapers = ref([]) // 存储选中的试卷ID
const viewDialogVisible = ref(false)
const currentQuestion = ref(null)

// 难度映射表
const difficultyMapping = ref({
  mapping: [],
  need_fit: false,
  last_fitted_at: null
})
const fitting = ref(false)

// 机构列表
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

const filters = reactive({
  keyword: '',
  question_type: '',
  difficultyMin: null,
  difficultyMax: null,
  source_type: '',
  source_institute: '',
  author: '',
  year: null,
  matchScope: ['paper', 'question'] // 默认匹配试卷和题目
})

const showAdvanced = ref(false)
const showDifficultyMap = ref(false)
const hasSearched = ref(false) // 标记是否执行过搜索
const composeMode = ref(false) // 组卷模式
const selectedQuestions = ref([]) // 组卷模式下选中的题目
const tableRefs = ref({}) // 存储各试卷表格的ref

// 难度输入框
const difficultyMinStr = ref('')
const difficultyMaxStr = ref('')

// 年份输入框
const yearStr = ref('')

function onYearInput(val) {
  // 只允许正整数
  let cleaned = val.replace(/[^\d]/g, '')
  // 限制4位数字
  if (cleaned.length > 4) cleaned = cleaned.slice(0, 4)
  yearStr.value = cleaned
  filters.year = cleaned ? parseInt(cleaned, 10) : null
}

function onDifficultyMinInput(val) {
  // 只允许数字和小数点
  let cleaned = val.replace(/[^\d.]/g, '')
  // 只保留第一个小数点
  const parts = cleaned.split('.')
  if (parts.length > 2) cleaned = parts[0] + '.' + parts.slice(1).join('')
  difficultyMinStr.value = cleaned
  // 约束：不能大于最大值
  const num = parseFloat(cleaned)
  if (!isNaN(num)) {
    if (num > 5) { difficultyMinStr.value = '5.0'; return }
    const maxVal = parseFloat(difficultyMaxStr.value)
    if (!isNaN(maxVal) && num > maxVal) {
      difficultyMaxStr.value = cleaned
    }
    filters.difficultyMin = num
  } else {
    filters.difficultyMin = null
  }
}

function onDifficultyMaxInput(val) {
  let cleaned = val.replace(/[^\d.]/g, '')
  const parts = cleaned.split('.')
  if (parts.length > 2) cleaned = parts[0] + '.' + parts.slice(1).join('')
  difficultyMaxStr.value = cleaned
  const num = parseFloat(cleaned)
  if (!isNaN(num)) {
    if (num > 5) { difficultyMaxStr.value = '5.0'; return }
    const minVal = parseFloat(difficultyMinStr.value)
    if (!isNaN(minVal) && num < minVal) {
      difficultyMinStr.value = cleaned
    }
    filters.difficultyMax = num
  } else {
    filters.difficultyMax = null
  }
}

function formatDifficulty(which) {
  if (which === 'min') {
    const num = parseFloat(difficultyMinStr.value)
    if (!isNaN(num)) {
      difficultyMinStr.value = num.toFixed(1)
      filters.difficultyMin = num
    }
  } else {
    const num = parseFloat(difficultyMaxStr.value)
    if (!isNaN(num)) {
      difficultyMaxStr.value = num.toFixed(1)
      filters.difficultyMax = num
    }
  }
}

const pagination = reactive({
  page: 1,
  perPage: 20,
  total: 0
})

const canEdit = computed(() => ['admin', 'teacher'].includes(authStore.userRole))

function canEditQuestion(question) {
  // 教师和管理员都有所有权限
  return ['admin', 'teacher'].includes(authStore.userRole)
}

function canDeleteQuestion(question) {
  // 教师和管理员都有所有权限
  return ['admin', 'teacher'].includes(authStore.userRole)
}

// 切换试卷选中状态（组卷模式下同时全选/取消全选该试卷下的题目）
function togglePaperSelection(paperId) {
  const idx = selectedPapers.value.indexOf(paperId)
  const group = groups.value.find(g => g.paper_id === paperId)
  
  if (idx >= 0) {
    selectedPapers.value.splice(idx, 1)
  } else {
    selectedPapers.value.push(paperId)
  }
  
  // 组卷模式下，通过 el-table 的 toggleRowSelection 控制题目全选
  if (composeMode.value && group) {
    const table = tableRefs.value[paperId]
    if (table) {
      const isSelected = selectedPapers.value.includes(paperId)
      group.questions.forEach(row => {
        table.toggleRowSelection(row, isSelected)
      })
    }
  }
}

// 批量删除试卷
async function batchDeletePapers() {
  if (selectedPapers.value.length === 0) return
  
  try {
    const count = selectedPapers.value.length
    let confirmText, confirmMsg
    
    if (count === 1) {
      // 单个删除，获取试卷名称
      const paperId = selectedPapers.value[0]
      const paper = groups.value.find(g => g.paper_id === paperId)
      const paperName = paper ? paper.paper_name : paperId
      confirmText = `确认删除${paperName}`
      confirmMsg = `确认删除 "${paperName}" 吗？此操作不可恢复！`
    } else {
      confirmText = `确认删除${count}套试题`
      confirmMsg = `确认删除选中的 ${count} 套试卷吗？此操作不可恢复！`
    }
    
    await ElMessageBox.prompt(
      `${confirmMsg}\n\n请在下方输入 "${confirmText}" 确认删除：`,
      '删除确认',
      {
        confirmButtonText: '确认删除',
        cancelButtonText: '取消',
        type: 'warning',
        inputPlaceholder: `请输入 ${confirmText}`,
        inputValidator: (value) => {
          if (value !== confirmText) {
            return `请输入 "${confirmText}" 确认删除`
          }
          return true
        }
      }
    )
    
    // 执行删除
    const selectedPaperKeys = selectedPapers.value
      .map(paperId => groups.value.find(g => g.paper_id === paperId)?.paper_key)
      .filter(Boolean)
    await api.post('/questions/batch-delete', {
      paper_keys: selectedPaperKeys,
      paper_ids: selectedPapers.value
    })
    
    ElMessage.success(`成功删除 ${count} 套试卷`)
    selectedPapers.value = []
    await loadQuestions()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败：' + (e.message || '未知错误'))
    }
  }
}

// 处理搜索按钮点击
function handleSearch() {
  hasSearched.value = true
  pagination.page = 1
  loadQuestions()
}

async function loadQuestions() {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      per_page: pagination.perPage,
      ...filters
    }
    // 移除空值和 matchScope（后端不需要）
    Object.keys(params).forEach(key => {
      if (params[key] === '' || params[key] === null || key === 'matchScope') {
        delete params[key]
      }
    })

    const res = await api.get('/questions', { params })
    let resultGroups = res.groups || []

    // 根据匹配范围过滤
    const matchPaper = filters.matchScope.includes('paper')
    const matchQuestion = filters.matchScope.includes('question')
    const expandedIndices = []
    matchedQuestionIds.value = new Set() // 重置匹配的题目ID

    // 如果两个都不选，返回空结果
    if (!matchPaper && !matchQuestion) {
      groups.value = []
      expandedPapers.value = []
      pagination.total = 0
      loading.value = false
      return
    }

    const keyword = filters.keyword?.toLowerCase() || ''

    // 试卷属性匹配函数（用于匹配试卷的整体属性）
    const paperAttrMatch = (group) => {
      // 题型：检查试卷中是否有题目符合该题型
      if (filters.question_type) {
        const hasMatch = group.questions.some(q => q.question_type === filters.question_type)
        if (!hasMatch) return false
      }
      // 难度：检查试卷的加权平均难度是否在范围内
      if (filters.difficultyMin !== null || filters.difficultyMax !== null) {
        const avgDifficulty = group.difficulty || 0
        if (filters.difficultyMin !== null && avgDifficulty < filters.difficultyMin) return false
        if (filters.difficultyMax !== null && avgDifficulty > filters.difficultyMax) return false
      }
      // 年份：检查试卷中是否有题目符合该年份
      if (filters.year) {
        const hasMatch = group.questions.some(q => q.year === filters.year)
        if (!hasMatch) return false
      }
      // 来源：检查试卷中是否有题目符合该来源
      if (filters.source_type) {
        const hasMatch = group.questions.some(q => q.source_type === filters.source_type)
        if (!hasMatch) return false
      }
      // 机构：检查试卷中是否有题目符合该机构
      if (filters.source_institute) {
        const hasMatch = group.questions.some(q => q.source_institute === filters.source_institute)
        if (!hasMatch) return false
      }
      // 作者：检查试卷中是否有题目符合该作者
      if (filters.author) {
        const hasMatch = group.questions.some(q => q.author === filters.author)
        if (!hasMatch) return false
      }
      return true
    }

    // 题目属性匹配函数
    const questionAttrMatch = (q) => {
      if (filters.question_type && q.question_type !== filters.question_type) return false
      if (filters.difficultyMin !== null && (q.difficulty || 0) < filters.difficultyMin) return false
      if (filters.difficultyMax !== null && (q.difficulty || 0) > filters.difficultyMax) return false
      if (filters.year && q.year !== filters.year) return false
      if (filters.source_type && q.source_type !== filters.source_type) return false
      if (filters.source_institute && q.source_institute !== filters.source_institute) return false
      if (filters.author && q.author !== filters.author) return false
      return true
    }

    // 题目关键词匹配函数
    const questionKeywordMatch = (q) => {
      if (!keyword) return true
      return (q.question_title && q.question_title.toLowerCase().includes(keyword)) ||
             (q.content && q.content.toLowerCase().includes(keyword)) ||
             (q.answer && q.answer.toLowerCase().includes(keyword))
    }

    // 处理匹配逻辑
    if (matchPaper && !matchQuestion) {
      // 只匹配试卷：关键词匹配试卷标题，其他条件匹配试卷属性
      resultGroups = resultGroups.filter((group, index) => {
        const paperTitleMatch = !keyword || group.paper_name.toLowerCase().includes(keyword)
        const attrMatch = paperAttrMatch(group)
        return paperTitleMatch && attrMatch
      })
    } else if (!matchPaper && matchQuestion) {
      // 只匹配题目：关键词匹配题目信息，其他条件匹配题目属性
      resultGroups = resultGroups.filter((group, index) => {
        const matchedQuestions = group.questions.filter(q => {
          return questionKeywordMatch(q) && questionAttrMatch(q)
        })
        if (matchedQuestions.length > 0) {
          expandedIndices.push(index)
          // 记录匹配的题目ID
          matchedQuestions.forEach(q => matchedQuestionIds.value.add(q.id))
          return true
        }
        return false
      })
    } else if (matchPaper && matchQuestion) {
      // 两个都匹配：试卷可以通过任一方式匹配，匹配题目的试卷要展开
      resultGroups = resultGroups.filter((group, index) => {
        // 试卷匹配方式
        const paperTitleMatch = !keyword || group.paper_name.toLowerCase().includes(keyword)
        const paperAttr = paperAttrMatch(group)
        const paperWay = paperTitleMatch && paperAttr

        // 题目匹配方式
        const matchedQuestions = group.questions.filter(q => {
          return questionKeywordMatch(q) && questionAttrMatch(q)
        })
        const questionWay = matchedQuestions.length > 0

        if (questionWay) {
          expandedIndices.push(index)
          matchedQuestions.forEach(q => matchedQuestionIds.value.add(q.id))
        }

        return paperWay || questionWay
      })
    }

    groups.value = resultGroups
    // 如果开启了匹配题目，自动展开包含匹配题目的试卷
    expandedPapers.value = matchQuestion && (keyword || filters.question_type || filters.difficultyMin !== null || filters.difficultyMax !== null || filters.year || filters.source_type || filters.source_institute || filters.author) ? expandedIndices : []
    pagination.total = res.total
  } catch (error) {
    // 错误已处理
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.keyword = ''
  filters.question_type = ''
  filters.difficultyMin = null
  filters.difficultyMax = null
  filters.source_type = ''
  filters.source_institute = ''
  filters.author = ''
  filters.year = null
  filters.matchScope = ['paper', 'question'] // 重置为默认
  difficultyMinStr.value = ''
  difficultyMaxStr.value = ''
  yearStr.value = ''
  pagination.page = 1
  hasSearched.value = false // 重置搜索标志
  loadQuestions()
}

function handleSourceTypeChange(val) {
  // 切换来源类型时清空机构、作者和年份筛选
  filters.source_institute = ''
  filters.author = ''
  filters.year = null
}

// 切换组卷模式
function toggleComposeMode() {
  composeMode.value = !composeMode.value
  if (composeMode.value) {
    // 进入组卷模式时，继承已选中的试卷，自动全选其下的所有题目
    selectedPapers.value.forEach(paperId => {
      const group = groups.value.find(g => g.paper_id === paperId)
      const table = tableRefs.value[paperId]
      if (group && table) {
        group.questions.forEach(row => {
          table.toggleRowSelection(row, true)
        })
      }
    })
  } else {
    // 退出组卷模式时清空选中
    selectedQuestions.value = []
  }
}

// 跳转到新建试卷界面
function goToCompose() {
  if (selectedQuestions.value.length === 0) {
    ElMessage.warning('请至少选择一道题目')
    return
  }
  
  // 将选中的题目保存到 sessionStorage
  sessionStorage.setItem('composeQuestions', JSON.stringify(selectedQuestions.value))
  
  // 跳转到新建试卷界面
  router.push('/questions/compose')
}

// 处理题目选择变化
function handleQuestionSelectionChange(selection, paperId) {
  // 更新全局选中题目列表
  const otherPaperQuestionIds = new Set()
  groups.value.forEach(g => {
    if (g.paper_id !== paperId) {
      g.questions.forEach(q => otherPaperQuestionIds.add(q.id))
    }
  })
  // 保留其他试卷的选中题目 + 当前试卷新选中的题目
  const otherSelected = selectedQuestions.value.filter(q => otherPaperQuestionIds.has(q.id))
  selectedQuestions.value = [...otherSelected, ...selection]
  
  // 同步试卷复选框状态：如果该试卷所有题目都选中了，则勾选试卷复选框
  const group = groups.value.find(g => g.paper_id === paperId)
  if (group && selection.length === group.questions.length) {
    if (!selectedPapers.value.includes(paperId)) {
      selectedPapers.value.push(paperId)
    }
  } else {
    const idx = selectedPapers.value.indexOf(paperId)
    if (idx >= 0) {
      selectedPapers.value.splice(idx, 1)
    }
  }
}

// 设置表格ref
function setTableRef(el, paperId) {
  if (el) {
    tableRefs.value[paperId] = el
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
      filters.source_institute = res.institute.code
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

// 点击试卷展开/收起
function togglePaperExpand(index) {
  const idx = expandedPapers.value.indexOf(index)
  if (idx > -1) {
    expandedPapers.value.splice(idx, 1)
  } else {
    expandedPapers.value.push(index)
  }
}

// 判断是否显示机构（只有全是历年真题时不显示）
function shouldShowInstitute(group) {
  // 检查试卷中是否全是历年真题
  const allPastExam = group.questions.every(q => q.source_type === 'past_exam')
  // 如果全是历年真题，不显示机构；如果有模拟题或混合，显示机构
  return !allPastExam
}

// 获取试卷涉及的机构
function getPaperInstitute(group) {
  const codes = [...new Set(group.questions.map(q => q.source_institute).filter(Boolean))]
  if (codes.length === 0) return '未知'
  // 将代码映射为中文名称
  return codes.map(code => {
    const inst = instituteList.value.find(i => i.code === code)
    return inst ? `${inst.name}（${code}）` : code
  }).join('，')
}

// 获取试卷总分
function getPaperTotalScore(group) {
  return group.questions.reduce((sum, q) => sum + (q.default_score || 0), 0)
}

// 获取试卷年份
function getPaperYear(group) {
  const years = [...new Set(group.questions.map(q => q.year).filter(Boolean))]
  return years.length > 0 ? years.join('，') : '未知'
}

// 获取试卷作者
function getPaperAuthors(group) {
  const authors = [...new Set(group.questions.map(q => q.author).filter(Boolean))]
  return authors.length > 0 ? authors.join('，') : '未知'
}

// 获取题目行的类名（用于高亮匹配的题目）
function getQuestionRowClass({ row }) {
  // 只有执行过搜索后才显示高亮
  if (hasSearched.value && matchedQuestionIds.value.has(row.id)) {
    return 'matched-question-row'
  }
  return ''
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
  if (!q || !q.content_images) return []
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
  if (!q || !q.answer_images) return []
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

function viewQuestion(question) {
  currentQuestion.value = question
  viewDialogVisible.value = true
}

// 试卷操作
function viewPaper(paper) {
  // 跳转到试卷详情页
  router.push(`/papers/${paper.paper_uuid}`)
}

function editPaper(group) {
  router.push(`/questions/${group.paper_uuid}`)
}

async function deletePaper(paper) {
  try {
    await ElMessageBox.confirm(`确定要删除试卷"${paper.paper_name}"吗？包含 ${paper.question_count} 道题目。`, '确认删除', {
      type: 'warning'
    })
    
    // 删除试卷下所有题目
    for (const q of paper.questions) {
      await api.delete(`/questions/${q.id}`)
    }
    
    ElMessage.success('删除成功')
    loadQuestions()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

function editQuestion(question) {
  router.push(`/questions/${question.id}/edit`)
}

async function deleteQuestion(question) {
  try {
    await ElMessageBox.confirm('确定要删除这道题目吗？', '确认删除', {
      type: 'warning'
    })
    
    await api.delete(`/questions/${question.id}`)
    ElMessage.success('删除成功')
    loadQuestions()
  } catch (error) {
    if (error !== 'cancel') {
      // 错误已处理
    }
  }
}

function truncateContent(content) {
  if (!content) return ''
  // 移除LaTeX标记
  let text = content.replace(/\$\$?/g, '').replace(/\\[a-zA-Z]+/g, '')
  text = text.replace(/[{}]/g, '')
  return text.length > 100 ? text.substring(0, 100) + '...' : text
}

// 标签映射
const questionTypeMap = {
  theory: { label: '理论题', type: '' },
  experiment: { label: '实验理论题', type: 'success' }
}

const sourceTypeMap = {
  past_exam: { label: '历年真题', type: '' },
  mock: { label: '模拟题', type: 'warning' }
}

const questionTypeLabel = (type) => questionTypeMap[type]?.label || type
const questionTypeTag = (type) => questionTypeMap[type]?.type || ''
const difficultyLabel = (d) => {
  if (typeof d === 'number') return d.toFixed(1)
  return d
}

const difficultyTag = (d) => {
  if (typeof d !== 'number') return ''
  if (d <= 1.5) return 'success'
  if (d <= 2.5) return ''
  if (d <= 3.5) return 'warning'
  return 'danger'
}
const sourceTypeLabel = (s) => sourceTypeMap[s]?.label || s
const sourceTypeTag = (s) => sourceTypeMap[s]?.type || ''

onMounted(() => {
  // 检查是否是从组卷界面返回
  const returnToCompose = sessionStorage.getItem('returnToComposeMode')
  const storedQuestions = sessionStorage.getItem('composeQuestions')

  if (returnToCompose === 'true' && storedQuestions) {
    // 恢复组卷模式和已选题目
    composeMode.value = true
    try {
      selectedQuestions.value = JSON.parse(storedQuestions)
    } catch (e) {
      console.error('解析选题数据失败', e)
    }
    // 清除标记
    sessionStorage.removeItem('returnToComposeMode')
  }

  resetFilters() // 每次进入页面时重置筛选条件
  loadQuestions()
  loadInstitutes()
  if (canEdit.value) {
    loadDifficultyMapping()
  }
})

// 加载难度映射表
async function loadDifficultyMapping() {
  try {
    const res = await api.get('/papers/difficulty-mapping')
    difficultyMapping.value = {
      mapping: res.mapping || [],
      need_fit: res.need_fit || false,
      last_fitted_at: res.last_fitted_at
    }
    // 如果有数据需要更新，自动重新拟合
    if (res.need_fit && res.mapping.length > 0) {
      await fitDifficultyMapping()
    }
  } catch (error) {
    console.error('加载难度映射表失败', error)
  }
}

// 重新拟合难度映射
async function fitDifficultyMapping() {
  fitting.value = true
  try {
    const res = await api.post('/papers/fit-difficulty-mapping')
    difficultyMapping.value = {
      mapping: res.mapping || [],
      need_fit: false,
      last_fitted_at: new Date().toISOString()
    }
    ElMessage.success(`拟合完成，共处理 ${res.fitted_count} 道题目`)
  } catch (error) {
    if (error.response?.data?.error) {
      ElMessage.error(error.response.data.error)
    } else {
      ElMessage.error('拟合失败')
    }
  } finally {
    fitting.value = false
  }
}
</script>

<style scoped>
.filter-card {
  margin-bottom: 20px;
}

.keyword-row {
  display: flex;
  align-items: center;
  margin-bottom: 0;
}

.advanced-filters {
  display: block;
}

.filter-row {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}

.filter-row:last-child {
  margin-bottom: 0;
}

.filter-row.multi-col {
  gap: 24px;
}

.filter-row .inline-item {
  margin-bottom: 0;
}

.difficulty-range {
  display: flex;
  align-items: center;
  gap: 8px;
}

.difficulty-sep {
  color: #909399;
  font-size: 14px;
}

/* 试卷列表样式 */
.paper-list {
  background: #fff;
  border-radius: 4px;
}

.paper-item {
  border-bottom: 1px solid #ebeef5;
  transition: background-color 0.2s;
}

.paper-item:hover {
  background-color: #f5f7fa;
}

.paper-header {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  cursor: pointer;
  user-select: none;
}

.paper-name {
  font-weight: 500;
}

.expand-icon {
  margin-left: auto;
  transition: transform 0.15s ease;
  color: #909399;
}

.expand-icon.expanded {
  transform: rotate(180deg);
}

.paper-content {
  padding: 0 16px 12px;
  background: #fafafa;
}

/* 隐藏 el-table selection 列的表头全选复选框 */
:deep(.el-table__header .el-checkbox__inner) {
  display: none;
}

/* 匹配的题目高亮（浅黄色） */
:deep(.matched-question-row) {
  background-color: #fffbe6 !important;
}

:deep(.matched-question-row td) {
  background-color: #fffbe6 !important;
}

.paper-summary {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 10px 16px;
  margin-top: 8px;
  background: #f0f2f5;
  border-radius: 4px;
  font-size: 13px;
  color: #606266;
}

.summary-item {
  display: flex;
  align-items: center;
}

/* 平滑展开动画 */
.expand-enter-active,
.expand-leave-active {
  transition: all 0.15s ease-out;
  overflow: hidden;
}

.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  max-height: 0;
  padding-top: 0;
  padding-bottom: 0;
}

.expand-enter-to,
.expand-leave-from {
  opacity: 1;
  max-height: 500px;
}

.group-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 500;
  font-size: 15px;
}

.action-bar {
  margin-bottom: 20px;
  display: flex;
  align-items: center;
}

.difficulty-map-module {
  margin-bottom: 20px;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  overflow: hidden;
  background: #fff;
}

.difficulty-map-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  background: #f5f7fa;
  border-bottom: 1px solid #ebeef5;
}

.difficulty-map-title {
  font-weight: 600;
  font-size: 14px;
  color: #303133;
}

.question-preview {
  line-height: 1.5;
  color: #606266;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}



.question-meta {
  margin-bottom: 12px;
}

.question-split-view {
  display: flex;
  gap: 16px;
  min-height: 400px;
}

.question-panel,
.answer-panel {
  flex: 0 0 calc(50% - 8px);
  width: calc(50% - 8px);
  min-width: 0;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.panel-header {
  padding: 10px 16px;
  font-weight: 600;
  font-size: 14px;
  color: #303133;
  background: #f5f7fa;
  border-bottom: 1px solid #ebeef5;
}

.question-panel .panel-header {
  border-left: 3px solid #409EFF;
}

.answer-panel .panel-header {
  border-left: 3px solid #67c23a;
}

.panel-body {
  padding: 16px;
  flex: 1;
  overflow-y: auto;
  line-height: 1.8;
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
