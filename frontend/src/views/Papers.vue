<template>
  <div class="papers-page">
    <!-- 试卷列表区域 -->
    <el-card>
      <template #header>
        <div class="card-header">
          <span>试卷列表</span>

        </div>
      </template>
      
      <el-table :data="papers" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        
        <el-table-column prop="title" label="试卷标题" min-width="250" />
        
        <el-table-column prop="total_score" label="总分" width="80" />
        
        <el-table-column label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="editPaper(row)" v-if="canEditPaper(row)">编辑</el-button>
            <el-button type="danger" link @click="deletePaper(row)" v-if="canEditPaper(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <div class="pagination">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.perPage"
          :total="pagination.total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @size-change="loadPapers"
          @current-change="loadPapers"
        />
      </div>
    </el-card>
    
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../utils/api'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

// 试卷列表
const loading = ref(false)
const papers = ref([])
const pagination = reactive({
  page: 1,
  perPage: 20,
  total: 0
})

function canEditPaper(paper) {
  if (authStore.userRole === 'admin') return true
  return paper.created_by === authStore.user?.id
}

async function loadPapers() {
  loading.value = true
  try {
    const res = await api.get('/papers', {
      params: {
        page: pagination.page,
        per_page: pagination.perPage
      }
    })
    papers.value = res.papers
    pagination.total = res.total
  } catch (error) {
    // 错误已处理
  } finally {
    loading.value = false
  }
}

function editPaper(paper) {
  router.push(`/papers/${paper.id}/edit`)
}

async function deletePaper(paper) {
  try {
    await ElMessageBox.confirm('确定要删除这份试卷吗？', '确认删除', {
      type: 'warning'
    })
    
    await api.delete(`/papers/${paper.id}`)
    ElMessage.success('删除成功')
    loadPapers()
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
  loadPapers()
})
</script>

<style scoped>
.papers-page {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
