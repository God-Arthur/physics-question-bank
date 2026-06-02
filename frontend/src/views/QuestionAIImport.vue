<template>
  <div class="ai-import-page">
    <!-- 步骤指引 -->
    <el-card class="step-card">
      <template #header>
        <div class="card-header">
          <span>批量导入题目</span>
        </div>
      </template>
      
      <el-steps :active="step" align-center>
        <el-step title="AI识别" />
        <el-step title="粘贴结果" />
        <el-step title="预览编辑" />
        <el-step title="确认导入" />
      </el-steps>
    </el-card>
    
    <!-- 步骤1：Prompt模板 -->
    <el-card v-if="step === 0" class="content-card">
      <template #header>
        <span>AI识别</span>
      </template>
      
      <el-alert type="info" :closable="false" style="margin-bottom: 15px">
        请在豆包网页版中上传试卷和答案的图片或扫描文件，然后输入以下提示词要求豆包识别文字
      </el-alert>
      
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px">
        <el-button @click="$router.push('/questions')">←返回</el-button>
        <div style="display: flex; gap: 10px">
          <el-button @click="copyPrompt">
            <el-icon><CopyDocument /></el-icon>
            复制提示词
          </el-button>
          <el-button type="primary" @click="step = 1">下一步→</el-button>
        </div>
      </div>
      
      <div class="prompt-box">
        <pre>{{ promptTemplate }}</pre>
      </div>
    </el-card>
    
    <!-- 步骤2：上传图片和粘贴json（左右两栏） -->
    <el-card v-if="step === 1" class="content-card">
      <template #header>
        <span>粘贴结果</span>
      </template>
      
      <!-- JSON 输入 -->
      <div>
        <el-input
          v-model="jsonInput"
          type="textarea"
          :rows="14"
          placeholder='格式：{"questions": [...], "answers": [...]} 或 {"questions": [...]}'
          style="font-family: monospace"
        />
      </div>
      
      <div style="margin-top: 20px; display: flex; justify-content: space-between">
        <el-button @click="$router.push('/questions')">← 返回</el-button>
        <div style="display: flex; gap: 10px">
          <el-button @click="$router.push('/questions')">取消</el-button>
          <el-button type="primary" @click="parseJson" :loading="parsing">
            解析并预览
          </el-button>
        </div>
      </div>
    </el-card>
    
    <!-- 步骤3：预览编辑 -->
    <el-card v-if="step === 2" class="content-card">
      <template #header>
        <div class="card-header">
          <span>预览编辑</span>
        </div>
      </template>
      
      <div class="questions-preview">
        <!-- 图片上传与裁剪区域 -->
        <div class="image-section-in-preview">
          <div style="margin-bottom: 8px">
            <div style="display: flex; gap: 12px; align-items: center; flex-wrap: wrap">
              <el-upload
                :action="uploadUrl"
                :headers="uploadHeaders"
                :data="uploadData"
                :on-success="handleImageSuccess"
                :show-file-list="false"
                multiple
                accept="image/*"
                :before-upload="checkFileSize"
              >
                <el-button type="primary" plain size="small">
                  <el-icon><Plus /></el-icon>
                  上传图片
                </el-button>
              </el-upload>
              
              <el-upload
                :action="uploadUrl"
                :headers="uploadHeaders"
                :data="uploadData"
                :on-success="handleImageSuccess"
                :show-file-list="false"
                accept=".pdf"
                :before-upload="checkFileSize"
              >
                <el-button type="primary" plain size="small">
                  <el-icon><Document /></el-icon>
                  上传PDF
                </el-button>
              </el-upload>
              
              <div v-if="uploadedImages.length > 0" class="select-all-checkbox" @click="toggleSelectAll" :title="isAllSelected ? '取消全选' : '全选'">
                <span style="font-size: 12px; color: #606266; white-space: nowrap;">全选</span>
                <div class="select-all-box" :class="{ checked: isAllSelected }">
                  <el-icon v-if="isAllSelected" :size="14"><Check /></el-icon>
                </div>
              </div>
            </div>
          </div>
          
          <div v-if="uploadedImages.length > 0" style="margin-bottom: 8px">
            <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap">
              <div 
                v-for="(img, idx) in uploadedImages" 
                :key="img.name || img.uid"
                class="uploaded-image-item"
                :class="{ 'image-selected': selectedImageNames.includes(img.name) }"
                @click="toggleImageSelection(img.name)"
              >
                <el-image :src="img.url" style="width: 80px; height: 60px" fit="contain" />
                <!-- 尺寸选择 -->
                <div class="image-size-select" @click.stop>
                  <el-select 
                    v-model="img.size" 
                    size="small" 
                    style="width: 52px"
                    @change="handleImageSizeChange(img)"
                  >
                    <el-option label="大" value="large" />
                    <el-option label="中" value="medium" />
                    <el-option label="小" value="small" />
                  </el-select>
                </div>
                <div class="image-checkbox" :class="{ checked: selectedImageNames.includes(img.name) }">
                  <el-icon v-if="selectedImageNames.includes(img.name)" :size="14"><Check /></el-icon>
                </div>
                <div class="image-hover-actions">
                  <div class="image-hover-btn" title="查看大图" @click.stop="handlePreviewImage(img)">
                    <el-icon :size="16"><ZoomIn /></el-icon>
                  </div>
                  <div class="image-hover-btn" title="删除" @click.stop="deleteSingleImage(img)">
                    <el-icon :size="16"><Delete /></el-icon>
                  </div>
                </div>
              </div>
            </div>
            <div style="margin-top: 10px; display: flex; gap: 1px; align-items: center">
              <el-button type="danger" size="small" :disabled="selectedImageNames.length === 0" @click="handleBatchDelete">
                <el-icon><Delete /></el-icon>
                删除选中
              </el-button>
              <el-button type="warning" size="small" @click="handleCropWithBoxes" :disabled="!hasBoxes">
                <el-icon><Crop /></el-icon>
                裁剪
              </el-button>
              <span style="font-size: 12px; color: #909399">已选 {{ selectedImageNames.length }} 张</span>
            </div>
          </div>
          
          <el-divider style="margin: 12px 0" />
        </div>
        
        <div class="questions-list">
          <div
            v-for="(q, index) in parsedQuestions"
            :key="index"
            class="question-card"
          >
            <!-- 题目标题栏 -->
            <div class="question-title" @click="toggleExpand(index)">
              <el-icon style="margin-right: 6px; transition: transform 0.2s" :style="{ transform: expandedQuestions.includes(index) ? 'rotate(90deg)' : '' }"><ArrowRight /></el-icon>
              <span>第{{ index + 1 }}题</span>
              <el-tag size="small" type="primary">{{ questionTypeLabel(q.question_type) }}</el-tag>
              <el-tag size="small" type="warning">{{ difficultyLabel(q.difficulty) }}</el-tag>
              
              <el-button type="danger" link size="small" @click.stop="removeQuestion(index)" style="margin-left: auto">
                删除
              </el-button>
            </div>
            
            <!-- 题目内容（可展开/收起） -->
            <div v-show="expandedQuestions.includes(index)" class="question-body">
              <el-form :model="q" label-width="70px" size="small">
                <el-row :gutter="10">
                  <el-col :span="4">
                    <el-form-item label="题型">
                      <el-select v-model="q.question_type" style="width: 100%">
                        <el-option label="理论题" value="theory" />
                        <el-option label="实验理论题" value="experiment" />
                      </el-select>
                    </el-form-item>
                  </el-col>
                  <el-col :span="4">
                    <el-form-item label="难度">
                      <el-input-number v-model="q.difficulty" :min="0.1" :max="5.0" :step="0.1" :precision="1" :controls="false" style="width: 100%" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="4">
                    <el-form-item label="分值">
                      <el-input-number v-model="q.default_score" :min="1" :max="999" :step="1" :precision="0" :controls="false" style="width: 100%" @blur="fixScore(q)" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="4">
                    <el-form-item label="年份">
                      <el-input-number v-model="q.year" :min="1900" :max="2100" :controls="false" style="width: 100%" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="作者">
                      <el-input v-model="q.author" placeholder="可选" />
                    </el-form-item>
                  </el-col>
                </el-row>
                
                <el-row :gutter="15">
                  <el-col :span="24">
                    <el-form-item label="试卷标题">
                      <el-input v-model="q.title" placeholder="如：第42届全国中学生物理竞赛复赛" />
                    </el-form-item>
                  </el-col>
                </el-row>
                
                <el-row :gutter="15">
                  <el-col :span="8">
                    <el-form-item label="来源类型">
                      <el-select v-model="q.source_type" placeholder="请选择" style="width: 100%">
                        <el-option label="历年真题" value="past_exam" />
                        <el-option label="模拟题" value="mock" />
                      </el-select>
                    </el-form-item>
                  </el-col>
                  <el-col :span="8" v-if="q.source_type === 'mock'">
                    <el-form-item label="机构">
                      <el-select 
                        v-model="q.source_institute" 
                        placeholder="请选择机构" 
                        style="width: 100%"
                        @change="(val) => handleInstituteChange(val, index)"
                      >
                        <el-option 
                          v-for="(inst, idx) in instituteList" 
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
                
                <el-form-item label="题干">
                  <div style="width: 100%">
                    <el-input
                      v-model="q.content"
                      type="textarea"
                      :rows="4"
                      placeholder="题干内容（支持LaTeX：行内$...$，块级$$...$$）"
                    />
                    <el-button type="primary" link size="small" @click="openPreview(index, 'content')" style="margin-top: 4px">
                      预览渲染
                    </el-button>
                  </div>
                  <!-- 题干关联图片 -->
                  <el-form-item label="关联图片" v-if="uploadedImages.length > 0" style="margin-top: 10px">
                    <el-checkbox-group v-model="q.content_images">
                      <el-checkbox
                        v-for="img in uploadedImages"
                        :key="img.name"
                        :label="img.name"
                      >
                        <el-image
                          :src="img.url"
                          style="width: 80px; height: 60px; vertical-align: middle; margin-left: 5px"
                          fit="contain"
                        />
                      </el-checkbox>
                    </el-checkbox-group>
                  </el-form-item>
                </el-form-item>
                
                <el-form-item label="答案">
                  <div style="width: 100%">
                    <el-input
                      v-model="q.answer"
                      type="textarea"
                      :rows="4"
                      placeholder="答案内容（支持LaTeX）"
                    />
                    <el-button type="primary" link size="small" @click="openPreview(index, 'answer')" style="margin-top: 4px">
                      预览渲染
                    </el-button>
                  </div>
                  <!-- 答案关联图片 -->
                  <el-form-item label="关联图片" v-if="uploadedImages.length > 0" style="margin-top: 10px">
                    <el-checkbox-group v-model="q.answer_images">
                      <el-checkbox
                        v-for="img in uploadedImages"
                        :key="img.name"
                        :label="img.name"
                      >
                        <el-image
                          :src="img.url"
                          style="width: 80px; height: 60px; vertical-align: middle; margin-left: 5px"
                          fit="contain"
                        />
                      </el-checkbox>
                    </el-checkbox-group>
                  </el-form-item>
                </el-form-item>
              </el-form>
            </div>
          </div>
        </div>
      </div>
      
      <div style="margin-top: 20px; display: flex; justify-content: space-between">
        <el-button @click="step = 1">← 返回修改json</el-button>
        <div style="display: flex; gap: 10px">
          <el-button @click="$router.push('/questions')">取消</el-button>
          <el-button type="primary" @click="submitImport" :loading="submitting">
            确认导入
          </el-button>
        </div>
      </div>
    </el-card>
    
    <!-- LaTeX实时预览弹窗：左编辑 + 右渲染 -->
    <el-dialog v-model="previewVisible" :title="previewTitle" width="1100px" top="5vh" destroy-on-close>
      <div class="preview-split">
        <!-- 左侧：LaTeX原文编辑 -->
        <div class="preview-edit-panel">
          <div class="preview-panel-label">LaTeX 原文（可编辑，实时渲染）</div>
          <el-input
            v-model="previewSource"
            type="textarea"
            :rows="22"
            placeholder="输入LaTeX内容..."
            style="font-family: 'Consolas', 'Monaco', monospace; font-size: 14px"
          />
        </div>
        <!-- 右侧：渲染结果 -->
        <div class="preview-render-panel">
          <div class="preview-panel-label">渲染预览</div>
          <div class="preview-box latex-content" v-html="previewHtml"></div>
        </div>
      </div>
    </el-dialog>
    
    <!-- 新建机构弹窗 -->
    <el-dialog v-model="instituteDialogVisible" title="新建机构" width="450px" :close-on-click-modal="false" :show-close="false">
      <el-alert type="warning" :closable="false" style="margin-bottom: 15px">
        检测到题目中包含未知机构（NUL），请新建对应机构后再导入
      </el-alert>
      <el-form :model="instituteForm" :rules="instituteRules" ref="instituteFormRef" label-width="90px" hide-required-asterisk>
        <el-form-item label="机构名称" prop="name">
          <el-input v-model="instituteForm.name" placeholder="如：兰阶" />
        </el-form-item>
        <el-form-item label="机构代码" prop="code">
          <el-input v-model="instituteForm.code" placeholder="3位大写字母" maxlength="3" style="text-transform: uppercase" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="instituteDialogVisible = false">稍后处理</el-button>
        <el-button type="primary" @click="submitInstitute" :loading="instituteSubmitting">创建机构</el-button>
      </template>
    </el-dialog>
    
    <!-- 机构管理弹窗 -->
    <el-dialog v-model="manageInstituteDialogVisible" title="机构管理" width="600px" :close-on-click-modal="false" :show-close="false">
      <div style="margin-bottom: 15px">
        <el-button type="primary" size="small" @click="openManageInstituteDialog">添加机构</el-button>
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
    
    <!-- 图片预览弹窗 -->
    <div v-if="previewImageVisible" class="preview-overlay-wrapper">
      <el-image-viewer
        :url-list="previewUrlList"
        :initial-index="previewIndex"
        @close="previewImageVisible = false"
        @switch="onViewerSwitch"
      />
      <!-- 矩形绘制 Canvas 叠加层（纯渲染） -->
      <canvas
        ref="drawCanvasRef"
        class="draw-canvas-overlay"
      ></canvas>
    </div>
    <!-- 复选框浮层（与 viewer 同级，fixed 定位） -->
    <div v-if="previewImageVisible" class="preview-floatbar" @keydown.enter.prevent="togglePreviewSelection">
      <div
        class="preview-checkbox-overlay"
        :class="{ checked: isCurrentSelected }"
        @click.stop="togglePreviewSelection"
        title="选中/取消 (Enter)"
      >
        <el-icon v-if="isCurrentSelected" :size="14"><Check /></el-icon>
      </div>
      <span class="preview-counter">{{ previewIndex + 1 }} / {{ uploadedImages.length }}</span>
    </div>
    <!-- 绘制矩形按钮 - 融入 el-image-viewer 工具栏 -->
    <button
      v-if="previewImageVisible"
      ref="drawRectBtnRef"
      class="draw-rect-btn"
      :class="{ active: isDrawMode }"
      @click="toggleDrawMode"
      :title="isDrawMode ? '退出绘制' : '绘制矩形'"
    >
      <el-icon :size="16"><Crop /></el-icon>
    </button>
    <!-- 删除本张图片的框按钮 -->
    <button
      v-if="previewImageVisible && currentImageBoxes.length > 0"
      class="clear-boxes-btn"
      @click="clearCurrentBoxes"
      title="删除本张图片的框"
    >
      <el-icon :size="16"><Delete /></el-icon>
    </button>
    
    <!-- 导入结果 -->
    <el-card v-if="step === 3" class="content-card">
      <template #header>
        <span>导入完成</span>
      </template>
      
      <el-result
        icon="success"
        title="导入成功"
        :sub-title="`成功导入 ${importResult.count} 道题目`"
      >
        <template #extra>
          <el-button type="primary" @click="$router.push('/questions')">查看题库</el-button>
          <el-button @click="resetAll">继续导入</el-button>
        </template>
      </el-result>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRouter, onBeforeRouteLeave } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../utils/api'
import { useAuthStore } from '../stores/auth'
import katex from 'katex'
import { ensureUploadSession, cleanupUploadSessionAuth, cleanupUploadSessionNoAuth } from '../utils/uploadSession'

const router = useRouter()
const authStore = useAuthStore()

const step = ref(0)
const jsonInput = ref('')
const parsing = ref(false)
const submitting = ref(false)
const parsedQuestions = ref([])
const expandedQuestions = ref([0])
const importResult = reactive({ count: 0 })

// 上传会话：用于暂存上传的图片/PDF拆页图，便于在取消/超时/登出时精确清理
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
const uploadedImages = ref([])

const selectedImageNames = ref([])
const previewImageVisible = ref(false)
const previewIndex = ref(0)

const isCurrentSelected = computed(() => {
  const img = uploadedImages.value[previewIndex.value]
  return img && selectedImageNames.value.includes(img.name)
})

const previewUrlList = computed(() => {
  return uploadedImages.value.map(img => img.url)
})

// 矩形绘制相关
const isDrawMode = ref(false)
const showRects = ref(false) // 控制是否显示已绘制的矩形
const drawCanvasRef = ref(null)
const drawRectBtnRef = ref(null)
const isDrawing = ref(false)
const drawStart = ref({ x: 0, y: 0 }) // 图片本地坐标
const drawEnd = ref({ x: 0, y: 0 }) // 图片本地坐标
// 为每张图片存储独立的框数据：{ filename: [{x, y, w, h}, ...], ... }
const imageBoxes = ref({})

// 当前图片的框数据
const currentImageBoxes = computed(() => {
  const currentImage = previewUrlList.value[previewIndex.value]
  if (!currentImage) return []
  const urlParts = currentImage.split('/')
  const filename = urlParts[urlParts.length - 1]
  return imageBoxes.value[filename] || []
})

// 新建机构弹窗
const instituteDialogVisible = ref(false)
const instituteSubmitting = ref(false)
const instituteFormRef = ref(null)
const instituteForm = reactive({ name: '', code: '' })
const instituteRules = {
  name: [{ required: true, message: '请输入机构名称', trigger: 'blur' }],
  code: [
    { required: true, message: '请输入机构代码', trigger: 'blur' },
    { pattern: /^[A-Z]{3}$/, message: '必须是3位大写字母', trigger: 'blur' }
  ]
}

// 机构管理弹窗
const manageInstituteDialogVisible = ref(false)
const manageInstituteSubmitting = ref(false)
const manageInstituteFormRef = ref(null)
const manageInstituteForm = reactive({ name: '', code: '', id: null })
const manageInstituteMode = ref('view') // 'view' | 'add' | 'edit'
const defaultInstituteCodes = ['AJZ', 'BOZ', 'FYU', 'LAN', 'PJI', 'PKU', 'QUA', 'SBO', 'THU', 'WMS', 'XES', 'XYZ', 'YFD', 'ZHM', 'ZHX', 'IND'] // 默认机构，禁止修改删除

// 预览弹窗
const previewVisible = ref(false)
const previewTitle = ref('')
const previewSource = ref('')
const previewHtml = ref('')
const previewQuestionIndex = ref(-1)
const previewField = ref('')

const uploadUrl = '/api/questions/upload'
const uploadHeaders = computed(() => ({
  Authorization: `Bearer ${authStore.token}`
}))

// 机构列表（动态获取）
const instituteList = ref([])



// 动态生成 Prompt 模板
const promptTemplate = computed(() => {
  // 生成机构列表字符串（排除 IND 和 NUL，两者在后面硬编码）
  const instituteLines = instituteList.value
    .filter(inst => inst.code !== 'IND' && inst.code !== 'NUL')
    .sort((a, b) => a.code.localeCompare(b.code))
    .map(inst => `   - ${inst.name} ${inst.code}`)
    .join('\n')

  return `你是一个物理竞赛题目识别专家。请分析上传的图片，提取所有物理题目信息并按以下json格式输出（只输出json，不要包含其他文字）：

题干部分：
{
  "questions": [
    {
      "index": "1",
      "question_title": "导电介质",
      "content": "题干内容（公式采取LaTeX格式，用$包裹，如 $F=ma$，行内公式用$...$，独立公式用$$...$$；物理量采用斜体，单位不用斜体，函数名不用斜体（如sin, cos, ln, log），微分算符d等算符不用斜体，自然常数e和圆周率π不用斜体）",
      "question_type": "theory",
      "difficulty": "2.5",
      "source_type": "mock",
      "title": "试卷标题",
      "source_institute": "LAN",
      "author": "作者",
      "year": 2026,
      "score": 40
    }
  ]
}

答案部分：
{
  "answers": [
    {
      "question_title": "导电介质",
      "content": "答案内容"
    }
  ]
}

总的输出格式是：
{
  "questions": [...],
  "answers": [...]
}

识别规则：
1.题号（index）：题目的一级题号，统一转换为阿拉伯数字
2.题目名称（question_title）：本题标题，若原试卷未表明本题标题，则总结一个
3.内容（content）：题干文字，不包含本题的一级题号和分值声明
4.题型（question_type）：理论题选theory，实验理论题选experiment
5.试卷类型（source_type）：真题为past_exam，模拟题为mock
6.难度（difficulty）：0.0~5.0之间，精确到小数点后一位，根据该题目与下列基准套卷的对比赋值，如高于复赛高难度低于决赛难度可设置为3.7
   - 1.0 全国中学生物理竞赛预赛难度，基准为第42届预赛
   - 2.0 全国中学生物理竞赛复赛低难度，基准为第40届复赛
   - 3.0 全国中学生物理竞赛复赛高难度，基准为第42届复赛
   - 4.0 全国中学生物理竞赛决赛难度，基准为第42届决赛
7.标题（title）：试卷标题
8.出题机构（source_institute）：出题机构的代码，由三个大写字母组成
${instituteLines}
   - 个人 IND
   - 不在列表上的其他机构 NUL
9.作者（author）：该题目为机构出题且作者未知时应省略，若为个人出题则必须添加，未知的个人作者则填写"未知"
10.年份（year）：试卷年份，若未知则默认为当前年份
11.分值（score）：本题分值，若未知则默认为40分
12.答案部分规则同上
13.只识别印刷体文字，忽略手写笔记、批注、划线等
14.若识别到换行，则将换行符转换为\\n
`
})

function copyPrompt() {
  navigator.clipboard.writeText(promptTemplate.value).then(() => {
    ElMessage.success('Prompt 已复制到剪贴板')
  }).catch(() => {
    const textarea = document.createElement('textarea')
    textarea.value = promptTemplate.value
    document.body.appendChild(textarea)
    textarea.select()
    document.execCommand('copy')
    document.body.removeChild(textarea)
    ElMessage.success('Prompt 已复制到剪贴板')
  })
}

function handleImageSuccess(response, file) {
  // 兜底：上传成功即认为“进入会话”，确保已有 uploadSession
  if (!uploadSession.value && response.session_id) {
    // 后端兼容模式可能会返回 session_id
    uploadSession.value = { session_id: response.session_id, secret: uploadSession.value?.secret }
  }

  if (response.files && Array.isArray(response.files)) {
    // PDF 多页返回
    response.files.forEach((it, idx) => {
      uploadedImages.value.push({
        name: it.filename,
        url: it.url,
        uid: `${file.uid}_${idx}`,
        is_pdf: true,
        source_pdf: response.filename,
        size: 'medium'
      })
    })
    ElMessage.success(`PDF上传成功，共 ${response.files.length} 页`)
  } else if (response.filename) {
    uploadedImages.value.push({
      name: response.filename,
      url: response.url || `/api/questions/tmp-images/${uploadSessionId.value}/${response.filename}`,
      uid: file.uid,
      size: 'medium'
    })
    ElMessage.success('上传成功')
  }
}

// 修改单张图片尺寸
async function handleImageSizeChange(img) {
  try {
    await ensureSessionReady()
    const token = authStore.token
    const res = await fetch(`/api/questions/resize-image?filename=${encodeURIComponent(img.name)}&size=${img.size}&session_id=${encodeURIComponent(uploadSessionId.value)}`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` }
    })
    const data = await res.json()
    if (data.error) {
      ElMessage.error(data.error)
      return
    }
    // 更新文件名和URL（可能因为格式转换而改变）
    if (data.filename && data.filename !== img.name) {
      img.name = data.filename
      img.url = data.url || `/api/questions/tmp-images/${uploadSessionId.value}/${data.filename}`
    }
    ElMessage.success('尺寸已更新')
  } catch (e) {
    ElMessage.error('尺寸更新失败')
  }
}

function handlePreviewImage(file) {
  const idx = uploadedImages.value.findIndex(x => (x.name || x.uid) === (file.name || file.uid))
  previewIndex.value = idx >= 0 ? idx : 0
  previewImageVisible.value = true
}

function onViewerSwitch(index) {
  previewIndex.value = index
}

function togglePreviewSelection() {
  const img = uploadedImages.value[previewIndex.value]
  if (img) {
    const idx = selectedImageNames.value.indexOf(img.name)
    if (idx > -1) {
      selectedImageNames.value.splice(idx, 1)
    } else {
      selectedImageNames.value.push(img.name)
    }
  }
}

// 全局键盘监听（el-image-viewer 内按 Enter/Space）
watch(previewImageVisible, (visible) => {
  function onKey(e) {
    if (!previewImageVisible.value) return
    // 拖动画框时禁止所有快捷键
    if (isDrawing.value) {
      e.preventDefault()
      e.stopPropagation()
      return
    }
    if (e.key === 'Enter') {
      e.preventDefault()
      togglePreviewSelection()
    }
  }
  if (visible) {
    window.addEventListener('keydown', onKey)
    onCleanup = () => window.removeEventListener('keydown', onKey)
  } else {
    if (onCleanup) onCleanup()
  }
})
let onCleanup = null

// 矩形绘制功能
function toggleDrawMode() {
  isDrawMode.value = !isDrawMode.value
  showRects.value = isDrawMode.value
  if (!isDrawMode.value) {
    clearCanvas()
  } else {
    currentImageBoxes.value.length && drawRects()
  }
}

function initCanvas() {
  const canvas = drawCanvasRef.value
  if (!canvas) return
  canvas.width = window.innerWidth
  canvas.height = window.innerHeight
}

function clearCanvas() {
  const canvas = drawCanvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  ctx.clearRect(0, 0, canvas.width, canvas.height)
}

// 获取图片元素及其变换信息（包括旋转角度和原始尺寸）
function getViewerImg() {
  const img = document.querySelector('.el-image-viewer__canvas img')
  if (!img) return null
  const rect = img.getBoundingClientRect()
  
  // 获取旋转角度（el-image-viewer 使用 90° 倍数：0, 90, 180, 270）
  const style = window.getComputedStyle(img)
  const transform = style.transform
  let rotate = 0
  if (transform && transform !== 'none') {
    const matrix = new DOMMatrix(transform)
    rotate = Math.round(Math.atan2(matrix.b, matrix.a) * (180 / Math.PI))
  }
  
  // 图片原始尺寸
  const naturalWidth = img.naturalWidth
  const naturalHeight = img.naturalHeight
  
  return { img, rect, rotate, naturalWidth, naturalHeight }
}

// 根据旋转角度交换宽高
function getRotatedSize(width, height, rotate) {
  const r = ((rotate % 360) + 360) % 360
  if (r === 90 || r === 270) {
    return { width: height, height: width }
  }
  return { width, height }
}

// 屏幕坐标 → 图片本地坐标（百分比 0~1，基于原始图片）
function screenToLocal(sx, sy) {
  const info = getViewerImg()
  if (!info) return null
  const { rect, rotate, naturalWidth, naturalHeight } = info
  
  // 图片中心
  const centerX = rect.left + rect.width / 2
  const centerY = rect.top + rect.height / 2
  
  // 获取旋转后的显示尺寸
  const displaySize = getRotatedSize(naturalWidth, naturalHeight, rotate)
  const scaleX = rect.width / displaySize.width
  const scaleY = rect.height / displaySize.height
  
  // 将屏幕坐标反向旋转
  const angle = -rotate * Math.PI / 180
  const dx = sx - centerX
  const dy = sy - centerY
  const rx = dx * Math.cos(angle) - dy * Math.sin(angle)
  const ry = dx * Math.sin(angle) + dy * Math.cos(angle)
  
  // 转换为原始图片的本地百分比坐标
  const lx = (rx / scaleX + naturalWidth / 2) / naturalWidth
  const ly = (ry / scaleY + naturalHeight / 2) / naturalHeight
  
  return { x: lx, y: ly }
}

// 图片本地坐标（百分比）→ 屏幕坐标（应用当前旋转）
function localToScreen(lx, ly) {
  const info = getViewerImg()
  if (!info) return null
  const { rect, rotate, naturalWidth, naturalHeight } = info
  
  // 图片中心
  const centerX = rect.left + rect.width / 2
  const centerY = rect.top + rect.height / 2
  
  // 获取旋转后的显示尺寸
  const displaySize = getRotatedSize(naturalWidth, naturalHeight, rotate)
  const scaleX = rect.width / displaySize.width
  const scaleY = rect.height / displaySize.height
  
  // 从原始图片百分比转换为未旋转时的屏幕偏移
  const dx = (lx - 0.5) * naturalWidth * scaleX
  const dy = (ly - 0.5) * naturalHeight * scaleY
  
  // 应用旋转
  const angle = rotate * Math.PI / 180
  const rx = dx * Math.cos(angle) - dy * Math.sin(angle)
  const ry = dx * Math.sin(angle) + dy * Math.cos(angle)
  
  return {
    x: centerX + rx,
    y: centerY + ry
  }
}

// 判断屏幕坐标是否在图片内（考虑旋转）
function isInsideImage(sx, sy) {
  const info = getViewerImg()
  if (!info) return false
  const { rect, rotate, naturalWidth, naturalHeight } = info
  
  // 图片中心
  const centerX = rect.left + rect.width / 2
  const centerY = rect.top + rect.height / 2
  
  // 获取旋转后的显示尺寸
  const displaySize = getRotatedSize(naturalWidth, naturalHeight, rotate)
  const scaleX = rect.width / displaySize.width
  const scaleY = rect.height / displaySize.height
  
  // 将屏幕坐标反向旋转
  const angle = -rotate * Math.PI / 180
  const dx = sx - centerX
  const dy = sy - centerY
  const rx = dx * Math.cos(angle) - dy * Math.sin(angle)
  const ry = dx * Math.sin(angle) + dy * Math.cos(angle)
  
  // 检查是否在原始图片范围内
  const localX = (rx / scaleX + naturalWidth / 2) / naturalWidth
  const localY = (ry / scaleY + naturalHeight / 2) / naturalHeight
  
  return localX >= 0 && localX <= 1 && localY >= 0 && localY <= 1
}

// 将本地坐标限制在 0~1 范围内
function clampLocal(val) {
  return Math.max(0, Math.min(1, val))
}

// 本地坐标 → 屏幕坐标（不应用旋转，用于 canvas 整体旋转）
function localToScreenNoRotate(lx, ly) {
  const info = getViewerImg()
  if (!info) return null
  const { rect, rotate, naturalWidth, naturalHeight } = info
  
  const centerX = rect.left + rect.width / 2
  const centerY = rect.top + rect.height / 2
  
  // 获取旋转后的显示尺寸（用于计算缩放）
  const displaySize = getRotatedSize(naturalWidth, naturalHeight, rotate)
  const scaleX = rect.width / displaySize.width
  const scaleY = rect.height / displaySize.height
  
  // 使用原始图片尺寸计算偏移
  const dx = (lx - 0.5) * naturalWidth * scaleX
  const dy = (ly - 0.5) * naturalHeight * scaleY
  
  return {
    x: centerX + dx,
    y: centerY + dy
  }
}

function drawRects() {
  const canvas = drawCanvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  if (!showRects.value) return

  const info = getViewerImg()
  if (!info) return
  const { rect, rotate } = info

  ctx.strokeStyle = '#409eff'
  ctx.lineWidth = 2

  // 保存状态并应用与图片相同的旋转变换
  ctx.save()
  const centerX = rect.left + rect.width / 2
  const centerY = rect.top + rect.height / 2
  ctx.translate(centerX, centerY)
  ctx.rotate(rotate * Math.PI / 180)
  ctx.translate(-centerX, -centerY)

  // 绘制已保存的矩形（在不旋转的坐标系中，然后整体旋转）
  currentImageBoxes.value.forEach(rect => {
    const tl = localToScreenNoRotate(rect.x, rect.y)
    const br = localToScreenNoRotate(rect.x + rect.w, rect.y + rect.h)
    if (!tl || !br) return
    ctx.strokeRect(tl.x, tl.y, br.x - tl.x, br.y - tl.y)
  })

  // 绘制当前正在画的矩形
  if (isDrawing.value) {
    const x = Math.min(drawStart.value.x, drawEnd.value.x)
    const y = Math.min(drawStart.value.y, drawEnd.value.y)
    const w = Math.abs(drawEnd.value.x - drawStart.value.x)
    const h = Math.abs(drawEnd.value.y - drawStart.value.y)
    const tl = localToScreenNoRotate(x, y)
    const br = localToScreenNoRotate(x + w, y + h)
    if (tl && br) {
      ctx.strokeRect(tl.x, tl.y, br.x - tl.x, br.y - tl.y)
    }
  }

  ctx.restore()
}

function onDrawMouseDown(e) {
  // 只在画框模式下处理
  if (!isDrawMode.value) return

  // 1. 如果点击在工具栏区域（包括画框按钮），放行让 Vue 处理
  if (e.target.closest('.el-image-viewer__actions')) {
    return
  }

  // 2. 如果不在图片区域，不处理
  if (!isInsideImage(e.clientX, e.clientY)) return

  // 3. 在图片区域，阻止 viewer 拖拽，开始画框
  e.stopPropagation()
  e.preventDefault()

  initCanvas()
  isDrawing.value = true
  const local = screenToLocal(e.clientX, e.clientY)
  if (local) {
    drawStart.value = { x: local.x, y: local.y }
    drawEnd.value = { x: local.x, y: local.y }
  }
}

function onDrawMouseMove(e) {
  if (!isDrawing.value) return
  // 阻止 el-image-viewer 处理
  e.stopPropagation()
  // 将坐标限制在图片范围内
  const info = getViewerImg()
  if (!info) return
  const { rect } = info
  const cx = Math.max(rect.left, Math.min(rect.right, e.clientX))
  const cy = Math.max(rect.top, Math.min(rect.bottom, e.clientY))
  const local = screenToLocal(cx, cy)
  if (local) {
    drawEnd.value = { x: clampLocal(local.x), y: clampLocal(local.y) }
  }
  drawRects()
}

function onDrawMouseUp(e) {
  if (!isDrawing.value) return
  e.stopPropagation()
  isDrawing.value = false

  const x = Math.min(drawStart.value.x, drawEnd.value.x)
  const y = Math.min(drawStart.value.y, drawEnd.value.y)
  const w = Math.abs(drawEnd.value.x - drawStart.value.x)
  const h = Math.abs(drawEnd.value.y - drawStart.value.y)

  if (w > 0.01 && h > 0.01) {
    const currentImage = previewUrlList.value[previewIndex.value]
    if (currentImage) {
      const urlParts = currentImage.split('/')
      const filename = urlParts[urlParts.length - 1]
      if (!imageBoxes.value[filename]) {
        imageBoxes.value[filename] = []
      }
      imageBoxes.value[filename].push({ x, y, w, h })
    }
  }

  drawRects()
}

// 监听预览窗口打开时初始化 canvas
let rafId = null
watch(previewImageVisible, (visible) => {
  if (visible) {
    isDrawMode.value = false
    showRects.value = false
    setTimeout(() => {
      initCanvas()
      // document 捕获阶段事件（画框）
      document.addEventListener('mousedown', onDrawMouseDown, true)
      document.addEventListener('mousemove', onDrawMouseMove, true)
      document.addEventListener('mouseup', onDrawMouseUp, true)
      // 持续重绘矩形（跟随图片缩放/旋转）
      function redrawLoop() {
        if (showRects.value || isDrawing.value) {
          drawRects()
        }
        rafId = requestAnimationFrame(redrawLoop)
      }
      rafId = requestAnimationFrame(redrawLoop)
    }, 100)
  } else {
    if (rafId) {
      cancelAnimationFrame(rafId)
      rafId = null
    }
    document.removeEventListener('mousedown', onDrawMouseDown, true)
    document.removeEventListener('mousemove', onDrawMouseMove, true)
    document.removeEventListener('mouseup', onDrawMouseUp, true)
  }
})

function checkFileSize(file) {
  // 文件大小限制已取消
  return true
}

// 是否有被选中的图片且有框（用于启用裁剪按钮）
const hasBoxes = computed(() => {
  return selectedImageNames.value.some(name => {
    const boxes = imageBoxes.value[name]
    return boxes && boxes.length > 0
  })
})

// 根据框裁剪被选中的图片
async function handleCropWithBoxes() {
  // 收集被选中的图片及其框数据
  const crops = []
  for (const filename of selectedImageNames.value) {
    const boxes = imageBoxes.value[filename]
    if (boxes && boxes.length > 0) {
      crops.push({
        filename: filename,
        boxes: boxes.map(r => ({ x: r.x, y: r.y, w: r.w, h: r.h }))
      })
    }
  }
  
  if (crops.length === 0) {
    ElMessage.warning('请先勾选要裁剪的图片，并在图片上画框')
    return
  }
  
  try {
    await ensureSessionReady()
    const token = authStore.token
    const res = await fetch('/api/questions/crop-with-boxes', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ session_id: uploadSessionId.value, crops })
    })
    const data = await res.json()
    if (data.error) { ElMessage.error(data.error); return }
    
    // 添加裁剪后的图片到列表
    for (const img of (data.images || [])) {
      if (!uploadedImages.value.find(u => u.name === img.filename)) {
        uploadedImages.value.push({ name: img.filename, url: img.url, uid: img.filename, size: 'medium' })
        // 自动勾选新图片
        if (!selectedImageNames.value.includes(img.filename)) {
          selectedImageNames.value.push(img.filename)
        }
      }
    }
    
    ElMessage.success(data.message || '裁剪完成')
    
    // 清空已裁剪图片的框
    for (const crop of crops) {
      delete imageBoxes.value[crop.filename]
    }
    drawRects()
  } catch (e) {
    ElMessage.error('裁剪失败')
  }
}

// 删除本张图片的所有框
function clearCurrentBoxes() {
  const currentImage = previewUrlList.value[previewIndex.value]
  if (!currentImage) return
  const urlParts = currentImage.split('/')
  const filename = urlParts[urlParts.length - 1]
  
  if (imageBoxes.value[filename]) {
    delete imageBoxes.value[filename]
    drawRects()
    ElMessage.success('已删除本张图片的框')
  }
}

function toggleImageSelection(name) {
  const idx = selectedImageNames.value.indexOf(name)
  if (idx > -1) {
    selectedImageNames.value.splice(idx, 1)
  } else {
    selectedImageNames.value.push(name)
  }
}

const isAllSelected = computed(() => {
  return uploadedImages.value.length > 0 && selectedImageNames.value.length === uploadedImages.value.length
})

function toggleSelectAll() {
  if (isAllSelected.value) {
    selectedImageNames.value = []
  } else {
    selectedImageNames.value = uploadedImages.value.map(img => img.name)
  }
}

function handleImageRemove(file) {
  const index = uploadedImages.value.findIndex(img => img.uid === file.uid)
  if (index > -1) uploadedImages.value.splice(index, 1)
}

function deleteSingleImage(img) {
  ElMessageBox.confirm(`确定删除这张图片吗？`, '确认删除', {
    confirmButtonText: '删除',
    cancelButtonText: '取消',
    type: 'warning',
    confirmButtonClass: 'el-button--danger'
  }).then(() => {
    const idx = uploadedImages.value.findIndex(x => (x.name || x.uid) === (img.name || img.uid))
    if (idx > -1) {
      uploadedImages.value.splice(idx, 1)
      const sIdx = selectedImageNames.value.indexOf(img.name)
      if (sIdx > -1) selectedImageNames.value.splice(sIdx, 1)
    }
  }).catch(() => {})
}

function handleBatchDelete() {
  const count = selectedImageNames.value.length
  ElMessageBox.confirm(`确定删除选中的 ${count} 张图片吗？`, '确认删除', {
    confirmButtonText: '删除',
    cancelButtonText: '取消',
    type: 'warning',
    confirmButtonClass: 'el-button--danger'
  }).then(() => {
    const toDelete = [...selectedImageNames.value]
    uploadedImages.value = uploadedImages.value.filter(img => !toDelete.includes(img.name))
    selectedImageNames.value = []
  }).catch(() => {})
}

// --- LaTeX 渲染 ---

function renderLatex(content) {
  if (!content) return ''
  try {
    let text = content
    // 先提取公式，用占位符保护，避免被HTML转义破坏
    const formulas = []
    // 块级公式 $$...$$
    text = text.replace(/\$\$([^$]+)\$\$/g, (match, latex) => {
      formulas.push({ type: 'display', latex })
      return `%%LATEX_FORMULA_${formulas.length - 1}%%`
    })
    // 行内公式 $...$
    text = text.replace(/\$([^$]+)\$/g, (match, latex) => {
      formulas.push({ type: 'inline', latex })
      return `%%LATEX_FORMULA_${formulas.length - 1}%%`
    })
    
    // 现在安全地转义HTML特殊字符（公式已被保护）
    text = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    
    // 还原公式并渲染
    text = text.replace(/%%LATEX_FORMULA_(\d+)%%/g, (match, idx) => {
      const f = formulas[parseInt(idx)]
      if (!f) return match
      try {
        return katex.renderToString(f.latex, { throwOnError: false, displayMode: f.type === 'display' })
      } catch {
        return `<code>${f.latex}</code>`
      }
    })
    
    text = text.replace(/\n/g, '<br>')
    return text
  } catch {
    return content
  }
}

// 打开预览弹窗
function openPreview(index, field) {
  const q = parsedQuestions.value[index]
  if (!q) return
  const content = q[field] || ''
  if (!content.trim()) { ElMessage.warning('内容为空，无法预览'); return }
  
  previewQuestionIndex.value = index
  previewField.value = field
  previewTitle.value = `第 ${index + 1} 题 - ${field === 'content' ? '题干预览' : '答案预览'}`
  previewSource.value = content
  previewHtml.value = renderLatex(content)
  previewVisible.value = true
}

// 实时渲染：监听左侧编辑
watch(previewSource, (val) => {
  previewHtml.value = renderLatex(val)
})

// 弹窗关闭时回写数据
watch(previewVisible, (val) => {
  if (!val && previewQuestionIndex.value >= 0) {
    const q = parsedQuestions.value[previewQuestionIndex.value]
    if (q && previewField.value) {
      q[previewField.value] = previewSource.value
    }
  }
})

// --- json 解析 ---

function extractJson(str) {
  if (!str || !str.trim()) return null
  let jsonStr = str.trim()
  const jsonMatch = jsonStr.match(/```(?:json)?\s*([\s\S]*?)```/)
  if (jsonMatch) jsonStr = jsonMatch[1].trim()
  try { return JSON.parse(jsonStr) } catch { return null }
}

function parseJson() {
  if (!jsonInput.value.trim()) {
    ElMessage.error('请输入JSON数据')
    return
  }
  
  parsing.value = true
  
  try {
    const data = extractJson(jsonInput.value)
    if (!data) {
      ElMessage.error('JSON解析失败，请检查格式是否正确')
      parsing.value = false
      return
    }
    
    // 支持格式：{questions: [...], answers: [...]} 或 {questions: [...]}
    let questions = []
    let answersMap = {}
    
    if (Array.isArray(data)) {
      ElMessage.error('JSON格式错误：顶层必须是对象，如 {"questions": [...]}')
      parsing.value = false
      return
    }
    
    if (data.questions && Array.isArray(data.questions)) {
      questions = data.questions
    } else {
      ElMessage.error('JSON格式错误：需要包含 "questions" 数组')
      parsing.value = false
      return
    }
    
    if (questions.length === 0) {
      ElMessage.warning('未识别到任何题目')
      parsing.value = false
      return
    }
    
    // 解析答案（可选）
    if (data.answers && Array.isArray(data.answers)) {
      data.answers.forEach((a, idx) => {
        if (typeof a === 'string') {
          answersMap[idx] = a
        } else if (a && typeof a === 'object') {
          const i = (a.index !== undefined ? parseInt(a.index) - 1 : idx)
          answersMap[i] = a.content || a.answer || ''
        }
      })
      
      // 检查是否有超出范围的答案
      const maxQuestionIdx = questions.length - 1
      for (const idxStr of Object.keys(answersMap)) {
        if (parseInt(idxStr) > maxQuestionIdx) {
          ElMessage.warning(`答案中第 ${parseInt(idxStr) + 1} 题的答案没有对应的题目，将被忽略`)
        }
      }
    }
    
    // 设置默认值
    parsedQuestions.value = questions.map((q, idx) => ({
      question_title: q.question_title || '',
      content: q.content || '',
      answer: q.answer || answersMap[idx] || '',
      question_type: q.question_type || 'theory',
      difficulty: parseFloat(q.difficulty) || 3.0,
      source_type: q.source_type || '',
      title: q.title || '',
      source_institute: q.source_institute || '',
      source_info: q.source_info || '',
      author: q.author || '',
      year: q.year || new Date().getFullYear(),
      default_score: q.score || q.default_score || 40,
      content_images: q.content_images || [],
      answer_images: q.answer_images || []
    }))
    
    expandedQuestions.value = [0]
    ElMessage.success(`成功解析 ${parsedQuestions.value.length} 道题目`)
    
    // 检查是否有NUL机构，强制要求新建
    const hasNul = parsedQuestions.value.some(q => q.source_institute === 'NUL')
    if (hasNul) {
      ElMessage.warning('检测到未知机构（NUL），请先新建对应机构')
      showInstituteDialog()
    }
    
    step.value = 2
  } catch (e) {
    ElMessage.error('JSON解析失败，请检查格式是否正确')
    console.error('json parse error:', e)
  } finally {
    parsing.value = false
  }
}





// 加载机构列表
async function loadInstitutes() {
  try {
    const res = await api.get('/institutes/')
    instituteList.value = res.institutes || []
  } catch (error) {
    // 错误已处理
  }
}

// 页面加载时获取机构列表
onMounted(() => {
  loadInstitutes()
})

// 进入“预览编辑”步骤时，提前创建上传会话，确保上传时能携带 session_id
watch(step, (v) => {
  if (v === 2) {
    ensureSessionReady().catch(() => {})
  }
})

// 跳转离开页面：视为取消创建，清理本次会话在 uploads 中的临时文件
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

// 10分钟无交互自动退出批量导入会话
const IDLE_MS = 10 * 60 * 1000
let idleTimer = null
let idleListening = false

function resetIdleTimer() {
  if (idleTimer) clearTimeout(idleTimer)
  idleTimer = setTimeout(async () => {
    // 若还停留在批量导入页（step>=1），视为会话超时
    if (step.value >= 1) {
      ElMessage.warning('10分钟未操作，已自动退出批量导入会话')
      await cleanupCurrentSession()
      resetAll()
      router.push('/questions')
    }
  }, IDLE_MS)
}

function startIdleListening() {
  if (idleListening) return
  idleListening = true
  const events = ['mousemove', 'mousedown', 'keydown', 'scroll', 'touchstart']
  events.forEach(e => window.addEventListener(e, resetIdleTimer, { passive: true }))
  resetIdleTimer()
}

function stopIdleListening() {
  if (!idleListening) return
  idleListening = false
  const events = ['mousemove', 'mousedown', 'keydown', 'scroll', 'touchstart']
  events.forEach(e => window.removeEventListener(e, resetIdleTimer))
  if (idleTimer) clearTimeout(idleTimer)
  idleTimer = null
}

watch(step, (v) => {
  if (v >= 1) startIdleListening()
  else stopIdleListening()
})

// 校验题目
// 分值失焦时修正非法值
function fixScore(q) {
  if (!q.default_score || q.default_score < 1 || !Number.isInteger(q.default_score)) {
    q.default_score = 40
  }
}

function validateQuestion(q) {
  const errors = []
  if (!q.title || !q.title.trim()) {
    errors.push('试卷标题不能为空')
  }
  const validTypes = ['theory', 'experiment']
  if (!validTypes.includes(q.question_type)) {
    errors.push('题型不能为空')
  }
  // 难度：0.1~5.0 的一位小数
  if (typeof q.difficulty !== 'number' || q.difficulty < 0.1 || q.difficulty > 5.0) {
    errors.push('难度必须在0.1~5.0之间')
  } else if (!/^\d\.\d$/.test(q.difficulty.toFixed(1))) {
    errors.push('难度必须是一位小数')
  }
  if (!q.year || q.year < 1900 || q.year > 2100) {
    errors.push('年份不能为空')
  }
  if (!q.source_type) {
    errors.push('来源类型不能为空')
  }
  // 模拟题时机构必填
  if (q.source_type === 'mock' && !q.source_institute) {
    errors.push('模拟题必须选择机构')
  }
  if (!q.content || !q.content.trim()) {
    errors.push('题干不能为空')
  }
  if (!q.answer || !q.answer.trim()) {
    errors.push('答案不能为空')
  }
  return errors
}

// 机构选择变化处理
function handleInstituteChange(val, index) {
  if (val === '__EDIT__') {
    // 打开机构管理弹窗（查看模式）
    manageInstituteMode.value = 'view'
    manageInstituteDialogVisible.value = true
    // 清空选择，让用户重新选择
    parsedQuestions.value[index].source_institute = ''
  }
}

// 展开/收起题目
function toggleExpand(index) {
  const idx = expandedQuestions.value.indexOf(index)
  if (idx >= 0) {
    expandedQuestions.value.splice(idx, 1)
  } else {
    expandedQuestions.value.push(index)
  }
}

function removeQuestion(index) {
  parsedQuestions.value.splice(index, 1)
}

function removeAll() {
  ElMessageBox.confirm('确定要清空所有题目吗？', '确认', { type: 'warning' }).then(() => {
    parsedQuestions.value = []
  }).catch(() => {})
}

async function submitImport() {
  if (parsedQuestions.value.length === 0) {
    ElMessage.warning('没有可导入的题目')
    return
  }

  submitting.value = true
  try {
    await ensureSessionReady()
    // 收集所有题目中引用的图片
    const imageFilenames = new Set()
    parsedQuestions.value.forEach(q => {
      const collectImages = (images) => {
        if (images && Array.isArray(images)) {
          images.forEach(img => {
            if (img.filename) imageFilenames.add(img.filename)
            if (img.url) {
              const parts = img.url.split('/')
              imageFilenames.add(parts[parts.length - 1])
            }
          })
        }
      }
      collectImages(q.content_images)
      collectImages(q.answer_images)
    })

    // 压缩所有图片为 200dpi JPEG
    if (imageFilenames.size > 0) {
      ElMessage.info('正在压缩图片...')
      try {
        await api.post('/questions/compress-images', {
          filenames: Array.from(imageFilenames),
          session_id: uploadSessionId.value
        })
      } catch (e) {
        console.error('图片压缩失败', e)
      }
    }

    // 只发送题目相关字段
    const cleanQuestions = parsedQuestions.value.map(q => ({
      question_title: q.question_title,
      content: q.content,
      answer: q.answer,
      question_type: q.question_type,
      difficulty: q.difficulty,
      source_type: q.source_type,
      title: q.title,
      source_institute: q.source_institute,
      source_info: q.source_info,
      author: q.author,
      year: q.year,
      default_score: q.default_score,
      content_images: (q.content_images || []).map(fname => {
        const img = uploadedImages.value.find(i => i.name === fname)
        return img ? { filename: fname, size: img.size || 'medium' } : fname
      }),
      answer_images: (q.answer_images || []).map(fname => {
        const img = uploadedImages.value.find(i => i.name === fname)
        return img ? { filename: fname, size: img.size || 'medium' } : fname
      })
    }))

    const res = await api.post('/questions/batch-import', {
      upload_session_id: uploadSessionId.value,
      questions: cleanQuestions
    })

    importResult.count = res.count || parsedQuestions.value.length
    step.value = 3
    ElMessage.success(`成功导入 ${importResult.count} 道题目`)
    // 导入成功后，本地也清掉上传会话（后端已做迁移+清理）
    await cleanupCurrentSession()
  } catch (error) {
    // 错误已处理
  } finally {
    submitting.value = false
  }
}

function resetAll() {
  step.value = 0
  jsonInput.value = ''
  parsedQuestions.value = []
  expandedQuestions.value = [0]
  importResult.count = 0
  uploadedImages.value = []
  selectedImageNames.value = []
}

function questionTypeLabel(type) {
  const map = { theory: '理论题', experiment: '实验理论题' }
  return map[type] || type
}

function difficultyLabel(d) {
  if (typeof d === 'number') {
    return d.toFixed(1)
  }
  return d
}

// --- 机构管理 ---

function showInstituteDialog() {
  instituteForm.name = ''
  instituteForm.code = ''
  instituteDialogVisible.value = true
}

async function submitInstitute() {
  if (!instituteFormRef.value) return
  await instituteFormRef.value.validate(async (valid) => {
    if (!valid) return
    instituteSubmitting.value = true
    try {
      await api.post('/institutes/', {
        name: instituteForm.name,
        code: instituteForm.code.toUpperCase()
      })
      ElMessage.success(`机构 ${instituteForm.code.toUpperCase()} 创建成功`)
      instituteDialogVisible.value = false
      // 刷新机构列表，更新 Prompt
      await loadInstitutes()
    } catch (e) {
      // 错误已处理
    } finally {
      instituteSubmitting.value = false
    }
  })
}

// 打开机构管理弹窗
function openManageInstituteDialog() {
  manageInstituteMode.value = 'add'
  manageInstituteForm.name = ''
  manageInstituteForm.code = ''
  manageInstituteForm.id = null
  manageInstituteDialogVisible.value = true
}

// 编辑机构
function editInstitute(inst) {
  if (defaultInstituteCodes.includes(inst.code)) {
    ElMessage.warning('默认机构禁止修改')
    return
  }
  manageInstituteMode.value = 'edit'
  manageInstituteForm.name = inst.name
  manageInstituteForm.code = inst.code
  manageInstituteForm.id = inst.id
  manageInstituteDialogVisible.value = true
}

// 删除机构
async function deleteInstitute(inst) {
  if (defaultInstituteCodes.includes(inst.code)) {
    ElMessage.warning('默认机构禁止删除')
    return
  }
  try {
    await ElMessageBox.confirm(`确定要删除机构 ${inst.name} (${inst.code}) 吗？`, '确认删除', {
      type: 'warning'
    })
    await api.delete(`/institutes/${inst.id}`)
    ElMessage.success('删除成功')
    await loadInstitutes()
  } catch (e) {
    // 取消或错误
  }
}

// 提交机构管理（添加/编辑）
async function submitManageInstitute() {
  if (!manageInstituteFormRef.value) return
  await manageInstituteFormRef.value.validate(async (valid) => {
    if (!valid) return
    manageInstituteSubmitting.value = true
    try {
      if (manageInstituteMode.value === 'add') {
        await api.post('/institutes/', {
          name: manageInstituteForm.name,
          code: manageInstituteForm.code.toUpperCase()
        })
        ElMessage.success(`机构 ${manageInstituteForm.code.toUpperCase()} 创建成功`)
        // 添加成功后清空表单，继续添加
        manageInstituteForm.name = ''
        manageInstituteForm.code = ''
      } else {
        await api.put(`/institutes/${manageInstituteForm.id}`, {
          name: manageInstituteForm.name,
          code: manageInstituteForm.code.toUpperCase()
        })
        ElMessage.success(`机构 ${manageInstituteForm.code.toUpperCase()} 修改成功`)
        // 编辑成功后关闭弹窗
        manageInstituteDialogVisible.value = false
      }
      await loadInstitutes()
    } catch (e) {
      // 错误已处理
    } finally {
      manageInstituteSubmitting.value = false
    }
  })
}
</script>

<style scoped>
.ai-import-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.step-card { margin-bottom: 20px; }
.content-card { margin-bottom: 20px; }

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.prompt-box {
  position: relative;
  background: #f5f7fa;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  padding: 20px;
}

.prompt-box pre {
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 13px;
  line-height: 1.6;
  color: #303133;
  margin: 0;
  padding-right: 120px;
}

.copy-btn {
  position: absolute;
  top: 15px;
  right: 15px;
}

.json-paste-label {
  font-weight: 500;
  margin-bottom: 8px;
  color: #303133;
  font-size: 14px;
}

/* 预览编辑 */
.questions-preview { margin-top: 10px; }

.question-card {
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  margin-bottom: 8px;
  overflow: hidden;
}

.question-title {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 15px;
  background: #fafafa;
  cursor: pointer;
  user-select: none;
}

.question-title:hover {
  background: #f0f2f5;
}

.question-title span { font-weight: 500; }

.question-body {
  padding: 15px;
  border-top: 1px solid #e4e7ed;
}

/* 审核区域 */
.review-area {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 8px;
}

.approve-all-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 15px;
  background: #fafafa;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  margin-bottom: 15px;
}

/* 自定义审核复选框 */
.custom-checkbox {
  width: 18px;
  height: 18px;
  border-radius: 2px;
  border: 2px solid #dcdfe6;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
}

.custom-checkbox:hover {
  border-color: #409eff;
}

/* 未选中：白底灰框 */
.checkbox-unchecked {
  background: #fff;
  border-color: #dcdfe6;
}

/* 选中通过：绿底白勾 */
.checkbox-pass {
  background-color: #67c23a;
  border-color: #67c23a;
}

.checkbox-pass .el-icon {
  color: #fff;
}

/* 选中不通过：红底白叉 */
.checkbox-fail {
  background-color: #f56c6c;
  border-color: #f56c6c;
}

.checkbox-fail .el-icon {
  color: #fff;
}

.review-dot {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  border: 2px solid #dcdfe6;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
  color: #fff;
  flex-shrink: 0;
}

.review-dot:hover {
  border-color: #409eff;
}

.review-dot-active {
  background-color: #409eff;
  border-color: #409eff;
}

.review-dot-pass {
  background-color: #67c23a;
  border-color: #67c23a;
}

.review-dot-fail {
  background-color: #f56c6c;
  border-color: #f56c6c;
}

.review-label {
  font-size: 12px;
  color: #909399;
  white-space: nowrap;
}

.validate-result {
  display: flex;
  align-items: center;
  gap: 3px;
  font-size: 12px;
  white-space: nowrap;
}

.validate-pass {
  color: #67c23a;
}

.validate-fail {
  color: #f56c6c;
}

:deep(.el-collapse-item__header) {
  background: #fafafa;
  padding: 0 15px;
  border-radius: 4px;
}

:deep(.el-collapse-item__content) {
  padding: 15px 20px;
}

/* 预览弹窗左右分栏 */
.preview-split {
  display: flex;
  gap: 15px;
  height: 70vh;
}

.preview-edit-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.preview-render-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.preview-panel-label {
  font-weight: 500;
  margin-bottom: 8px;
  color: #606266;
  font-size: 13px;
  flex-shrink: 0;
}

.preview-edit-panel :deep(.el-textarea__inner) {
  height: 100% !important;
  min-height: 100% !important;
  resize: none;
}

.preview-box {
  flex: 1;
  padding: 20px;
  background: #fafafa;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  overflow-y: auto;
  line-height: 1.8;
  font-size: 15px;
}

/* 已上传图片列表 */
.uploaded-image-item {
  position: relative;
  border: 2px solid #e4e7ed;
  border-radius: 6px;
  padding: 4px;
  cursor: pointer;
  transition: border-color 0.2s;
  background: #fff;
}

.uploaded-image-item:hover {
  border-color: #409eff;
}

.uploaded-image-item.image-selected {
  border-color: #409eff;
  background: #ecf5ff;
}

.image-size-select {
  position: absolute;
  bottom: 2px;
  left: 2px;
  z-index: 1;
}

.image-size-select .el-select {
  font-size: 11px;
}

.image-checkbox {
  position: absolute;
  top: 2px;
  right: 2px;
  width: 16px;
  height: 16px;
  border: 2px solid #dcdfe6;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  z-index: 3;
}

.image-checkbox.checked {
  background: #409eff;
  border-color: #409eff;
  color: #fff;
}

/* 悬浮操作图标组 */
.image-hover-actions {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  align-items: center;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.2s;
  z-index: 2;
}

.uploaded-image-item:hover .image-hover-actions {
  opacity: 1;
}

.image-hover-btn {
  width: 28px;
  height: 28px;
  border-radius: 4px;
  color: #909399;
  background: rgba(255,255,255,0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: color 0.15s;
}

.image-hover-btn:hover {
  color: #409eff;
}

.image-hover-btn:nth-child(2):hover {
  color: #f56c6c;
}

.select-all-checkbox {
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  user-select: none;
  padding: 2px 0;
}

.select-all-checkbox:hover {
  opacity: 0.8;
}

.select-all-box {
  width: 16px;
  height: 16px;
  border: 2px solid #dcdfe6;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  flex-shrink: 0;
}

.select-all-box.checked {
  background: #409eff;
  border-color: #409eff;
  color: #fff;
}

/* 图片预览——el-image-viewer 顶栏叠加 */
.preview-overlay-wrapper {
  position: fixed;
  inset: 0;
  z-index: 3000;
}

.preview-floatbar {
  position: fixed;
  bottom: 50px;
  right: 40px;
  display: flex;
  align-items: center;
  gap: 10px;
  z-index: 3100;
  pointer-events: none;
}

.preview-floatbar > * {
  pointer-events: auto;
}

.preview-checkbox-overlay {
  width: 20px;
  height: 24px;
  border: 2px solid rgba(255,255,255,0.85);
  background: rgba(0,0,0,0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
  color: #fff;
  border-radius: 3px;
}

.preview-checkbox-overlay.checked {
  background: #409eff;
  border-color: #409eff;
}

.preview-counter {
  font-size: 13px;
  color: #fff;
  user-select: none;
  background: rgba(0,0,0,0.3);
  padding: 2px 8px;
  border-radius: 4px;
}

/* 矩形绘制 Canvas 叠加层（z-index 高于工具栏，框显示在工具栏之上） */
.draw-canvas-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: 2002003;
  pointer-events: none;
}

/* 绘制矩形按钮 - fixed 定位到工具栏右边，高度与工具栏一致 */
.draw-rect-btn {
  position: fixed;
  bottom: 30px;
  left: 50%;
  transform: translateX(220px);
  width: 40px;
  height: 40px;
  border-radius: 4px;
  border: none;
  background: rgba(255, 255, 255, 0.15);
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
  z-index: 2002003;
}

.draw-rect-btn:hover {
  background: rgba(255, 255, 255, 0.3);
}

.draw-rect-btn.active {
  background: #409eff;
}

/* 删除框按钮 - 位于画图按钮右侧 */
.clear-boxes-btn {
  position: fixed;
  bottom: 28px;
  left: 50%;
  transform: translateX(265px);
  width: 40px;
  height: 40px;
  border-radius: 4px;
  border: none;
  background: rgba(255, 255, 255, 0.15);
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
  z-index: 2002003;
}

.clear-boxes-btn:hover {
  background: rgba(245, 108, 108, 0.8);
}
</style>

<style>
/* 全局样式：工具栏 z-index、透明度和指针事件 */
.el-image-viewer__actions {
  z-index: 2002002 !important;
  background-color: rgba(0, 0, 0, 0.2) !important;
}

.el-image-viewer__actions__inner {
  pointer-events: auto !important;
}
</style>
