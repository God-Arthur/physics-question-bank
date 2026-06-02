<template>
  <div class="my-exams-page" v-loading="loading">
    <h2 style="margin-bottom: 20px">我的考试</h2>

    <el-table :data="exams" border stripe v-if="exams.length > 0">
      <el-table-column prop="title" label="考试名称" min-width="200">
        <template #default="{ row }">
          <el-link type="primary" @click="goDetail(row.publish_id)">{{ row.title }}</el-link>
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
      <el-table-column label="状态" width="120">
        <template #default="{ row }">
          <el-tag :type="getExamStatus(row).type" size="small">
            {{ getExamStatus(row).label }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="成绩" width="100">
        <template #default="{ row }">
          <span v-if="row.scoring_finished">已登记</span>
          <span v-else>-</span>
        </template>
      </el-table-column>
    </el-table>

    <el-empty v-else description="暂无考试" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../utils/api'

const router = useRouter()
const loading = ref(false)
const exams = ref([])

function getExamStatus(row) {
  const statusMap = {
    '未开始': { type: 'info', label: '未开始' },
    '进行中': { type: 'success', label: '进行中' },
    '已结束': { type: 'danger', label: '已结束' }
  }
  return statusMap[row.status] || { type: 'info', label: row.status }
}

function goDetail(publishId) {
  router.push(`/my-exams/${publishId}`)
}

async function loadExams() {
  loading.value = true
  try {
    const res = await api.get('/papers/my-exams')
    exams.value = res.exams || []
  } catch {
    ElMessage.error('加载考试列表失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadExams()
})
</script>

<style scoped>
.my-exams-page {
  padding: 0;
}
</style>
