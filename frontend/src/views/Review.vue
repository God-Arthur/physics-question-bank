<template>
  <div class="review-page">
    <el-tabs v-model="activeTab">
      <el-tab-pane label="待审核试卷" name="pending">
        <el-card>
          <el-table :data="pendingPapers.slice((pendingPage - 1) * pendingPageSize, pendingPage * pendingPageSize)" v-loading="loading" stripe>
            <el-table-column prop="title" label="试卷标题" min-width="200" />
            
            <el-table-column label="创建者" width="120">
              <template #default="{ row }">
                {{ row.creator?.real_name || '-' }}
              </template>
            </el-table-column>
            
            <el-table-column label="审核备注" min-width="200">
              <template #default="{ row }">
                {{ row.review_note || '-' }}
              </template>
            </el-table-column>
            
            <el-table-column label="创建时间" width="180">
              <template #default="{ row }">
                {{ formatDate(row.created_at) }}
              </template>
            </el-table-column>
            
            <el-table-column label="操作" width="150" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" link @click="viewPaper(row)">查看</el-button>
                <el-button type="success" link @click="showReviewDialog(row)">审核</el-button>
              </template>
            </el-table-column>
          </el-table>
          
          <el-pagination
            v-model:current-page="pendingPage"
            v-model:page-size="pendingPageSize"
            :page-sizes="[10, 20, 50, 100]"
            :total="pendingPapers.length"
            layout="total, sizes, prev, pager, next"
            style="margin-top: 15px; justify-content: flex-end"
          />
        </el-card>
      </el-tab-pane>
      
      <el-tab-pane label="已审核试卷" name="reviewed">
        <el-card>
          <el-table :data="reviewedPapers.slice((reviewedPage - 1) * reviewedPageSize, reviewedPage * reviewedPageSize)" v-loading="loadingReviewed" stripe>
            <el-table-column prop="title" label="试卷标题" min-width="200" />
            
            <el-table-column label="创建者" width="120">
              <template #default="{ row }">
                {{ row.creator?.real_name || '-' }}
              </template>
            </el-table-column>
            
            <el-table-column label="审核状态" width="100">
              <template #default="{ row }">
                <el-tag :type="row.review_status === 'approved' ? 'success' : 'danger'">
                  {{ row.review_status === 'approved' ? '已通过' : '已驳回' }}
                </el-tag>
              </template>
            </el-table-column>
            
            <el-table-column label="审核意见" min-width="200">
              <template #default="{ row }">
                {{ row.review_comment || '-' }}
              </template>
            </el-table-column>
            
            <el-table-column label="审核时间" width="180">
              <template #default="{ row }">
                {{ formatDate(row.reviewed_at) }}
              </template>
            </el-table-column>
            
            <el-table-column label="操作" width="100" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" link @click="viewPaper(row)">查看</el-button>
              </template>
            </el-table-column>
          </el-table>
          
          <el-pagination
            v-model:current-page="reviewedPage"
            v-model:page-size="reviewedPageSize"
            :page-sizes="[10, 20, 50, 100]"
            :total="reviewedPapers.length"
            layout="total, sizes, prev, pager, next"
            style="margin-top: 15px; justify-content: flex-end"
          />
        </el-card>
      </el-tab-pane>
    </el-tabs>
    
    <!-- 审核对话框 -->
    <el-dialog v-model="reviewDialogVisible" title="试卷审核" width="600px">
      <template v-if="currentPaper">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="试卷标题">{{ currentPaper.title }}</el-descriptions-item>
          <el-descriptions-item label="学校">{{ currentPaper.school || '-' }}</el-descriptions-item>
          <el-descriptions-item label="考试时长">{{ currentPaper.duration }}分钟</el-descriptions-item>
          <el-descriptions-item label="总分">{{ currentPaper.total_score }}分</el-descriptions-item>
          <el-descriptions-item label="审核备注">{{ currentPaper.review_note || '-' }}</el-descriptions-item>
        </el-descriptions>
        
        <div class="questions-preview" v-if="currentPaper.questions?.length">
          <h4>题目列表</h4>
          <div v-for="(item, index) in currentPaper.questions" :key="index" class="question-item">
            <div class="question-header">
              <span>第{{ index + 1 }}题</span>
              <el-tag type="warning">{{ item.score }}分</el-tag>
            </div>
            <div class="question-content">{{ truncateContent(item.question.content) }}</div>
          </div>
        </div>
        
        <el-divider />
        
        <el-form label-width="80px">
          <el-form-item label="审核结果">
            <el-radio-group v-model="reviewForm.status">
              <el-radio label="approved">通过</el-radio>
              <el-radio label="rejected">驳回</el-radio>
            </el-radio-group>
          </el-form-item>
          
          <el-form-item label="审核意见">
            <el-input
              v-model="reviewForm.comment"
              type="textarea"
              :rows="4"
              placeholder="请输入审核意见"
            />
          </el-form-item>
        </el-form>
      </template>
      
      <template #footer>
        <el-button @click="reviewDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitReview" :loading="submitting">提交审核</el-button>
      </template>
    </el-dialog>
    
    <!-- 查看试卷对话框 -->
    <el-dialog v-model="viewDialogVisible" title="试卷详情" width="800px">
      <template v-if="currentPaper">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="试卷标题">{{ currentPaper.title }}</el-descriptions-item>
          <el-descriptions-item label="学校">{{ currentPaper.school || '-' }}</el-descriptions-item>
          <el-descriptions-item label="考试时长">{{ currentPaper.duration }}分钟</el-descriptions-item>
          <el-descriptions-item label="总分">{{ currentPaper.total_score }}分</el-descriptions-item>
          <el-descriptions-item label="审核状态" :span="2">
            <el-tag :type="currentPaper.review_status === 'approved' ? 'success' : currentPaper.review_status === 'rejected' ? 'danger' : 'warning'">
              {{ currentPaper.review_status === 'approved' ? '已通过' : currentPaper.review_status === 'rejected' ? '已驳回' : '待审核' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="审核备注" :span="2">{{ currentPaper.review_note || '-' }}</el-descriptions-item>
          <el-descriptions-item label="审核意见" :span="2" v-if="currentPaper.review_comment">
            {{ currentPaper.review_comment }}
          </el-descriptions-item>
        </el-descriptions>
        
        <div class="questions-preview" v-if="currentPaper.questions?.length">
          <h4>题目列表</h4>
          <div v-for="(item, index) in currentPaper.questions" :key="index" class="question-item">
            <div class="question-header">
              <span>第{{ index + 1 }}题</span>
              <el-tag type="warning">{{ item.score }}分</el-tag>
            </div>
            <div class="question-content">{{ truncateContent(item.question.content) }}</div>
          </div>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../utils/api'

const activeTab = ref('pending')
const loading = ref(false)
const loadingReviewed = ref(false)
const pendingPapers = ref([])
const reviewedPapers = ref([])
const reviewDialogVisible = ref(false)
const viewDialogVisible = ref(false)
const currentPaper = ref(null)
const submitting = ref(false)

// 分页
const pendingPage = ref(1)
const pendingPageSize = ref(20)
const reviewedPage = ref(1)
const reviewedPageSize = ref(20)

const reviewForm = reactive({
  status: 'approved',
  comment: ''
})

async function loadPendingPapers() {
  loading.value = true
  try {
    const res = await api.get('/papers/pending-review')
    pendingPapers.value = res.papers
  } catch (error) {
    // 错误已处理
  } finally {
    loading.value = false
  }
}

async function loadReviewedPapers() {
  loadingReviewed.value = true
  try {
    const res = await api.get('/papers/my-reviews')
    reviewedPapers.value = res.papers
  } catch (error) {
    // 错误已处理
  } finally {
    loadingReviewed.value = false
  }
}

async function viewPaper(paper) {
  try {
    const res = await api.get(`/papers/${paper.id}`)
    currentPaper.value = res.paper
    viewDialogVisible.value = true
  } catch (error) {
    // 错误已处理
  }
}

function showReviewDialog(paper) {
  currentPaper.value = paper
  reviewForm.status = 'approved'
  reviewForm.comment = ''
  reviewDialogVisible.value = true
}

async function submitReview() {
  if (!reviewForm.comment && reviewForm.status === 'rejected') {
    ElMessage.warning('驳回时请填写审核意见')
    return
  }
  
  submitting.value = true
  try {
    await api.post(`/papers/${currentPaper.value.id}/review`, {
      review_status: reviewForm.status,
      review_comment: reviewForm.comment
    })
    ElMessage.success('审核完成')
    reviewDialogVisible.value = false
    loadPendingPapers()
    loadReviewedPapers()
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
  return text.length > 150 ? text.substring(0, 150) + '...' : text
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

onMounted(() => {
  loadPendingPapers()
  loadReviewedPapers()
})
</script>

<style scoped>
.review-page {
  padding: 20px;
}

.questions-preview {
  margin-top: 20px;
}

.questions-preview h4 {
  margin-bottom: 15px;
  color: #303133;
}

.question-item {
  padding: 15px;
  margin-bottom: 10px;
  background: #f5f7fa;
  border-radius: 4px;
}

.question-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-weight: 500;
}

.question-content {
  color: #606266;
  line-height: 1.6;
}
</style>
