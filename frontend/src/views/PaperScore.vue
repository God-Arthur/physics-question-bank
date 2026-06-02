<template>
  <div class="paper-score-page" v-loading="loading">
    <div class="page-header">
      <el-button @click="goBack">
        <el-icon><ArrowLeft /></el-icon>
        返回
      </el-button>
      <div style="flex: 1; text-align: center">
        <h3 style="margin: 0">{{ paperInfo.title }} - 成绩登记</h3>
        <div style="font-size: 13px; color: #909399; margin-top: 4px">
          总分: {{ paperInfo.total_score }} 分 | 难度系数: {{ (paperInfo.difficulty || 0).toFixed(2) }}
          <el-tag v-if="paperInfo.finished_at" type="success" size="small" style="margin-left: 8px">
            已结束登记
          </el-tag>
        </div>
      </div>
      <div style="display: flex; gap: 8px" v-if="!paperInfo.finished_at">
        <el-button type="warning" @click="finishScoring" :loading="finishing">结束登记</el-button>
        <el-button type="primary" @click="saveScores" :loading="saving">保存成绩</el-button>
      </div>
    </div>

    <el-card v-if="questions.length > 0 && students.length > 0">
      <el-table :data="tableData" border stripe style="width: 100%">
        <el-table-column prop="student_name" label="姓名" width="120" fixed="left" />

        <el-table-column label="状态" width="90" align="center" fixed="left" v-if="!paperInfo.finished_at">
          <template #default="{ row }">
            <el-checkbox v-if="!row.isAverage" v-model="row.absent" @change="onAbsentChange(row)">未参加</el-checkbox>
          </template>
        </el-table-column>

        <el-table-column
          v-for="(q, index) in questions"
          :key="q.question_id"
          :label="`第${index + 1}题`"
          :width="100"
          align="center"
        >
          <template #default="{ row }">
            <template v-if="row.isAverage">
              <span style="font-weight: bold; color: #409EFF">{{ row.scores[q.question_id]?.toFixed(1) || 0 }}</span>
            </template>
            <template v-else-if="paperInfo.finished_at || row.absent">
              <span>{{ row.absent ? '-' : (row.scores[q.question_id] || 0) }}</span>
              <div v-if="!row.absent" style="font-size: 11px; color: #909399">/{{ q.max_score }}</div>
            </template>
            <template v-else>
              <el-input-number
                v-model="row.scores[q.question_id]"
                :min="0"
                :max="q.max_score"
                :controls="false"
                size="small"
                style="width: 60px"
                @change="updateTotal(row)"
              />
              <div style="font-size: 11px; color: #909399">/{{ q.max_score }}</div>
            </template>
          </template>
        </el-table-column>

        <el-table-column label="总分" width="90" align="center" fixed="right">
          <template #default="{ row }">
            <span v-if="row.isAverage" style="font-weight: bold; color: #409EFF; font-size: 15px">{{ row.total_score?.toFixed(1) || 0 }}</span>
            <span v-else style="font-weight: bold; font-size: 15px">{{ row.total_score }}</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-empty v-else-if="!loading" description="暂无数据" />

    <!-- 总分排名 -->
    <el-card v-if="rankings.length > 0" style="margin-top: 20px">
      <template #header>
        <div class="card-header">
          <span>总分排名</span>
        </div>
      </template>
      <el-table :data="rankings" border stripe style="width: 100%">
        <el-table-column type="index" label="排名" width="80" align="center">
          <template #default="{ $index }">
            <el-tag v-if="$index === 0" type="danger" size="small">第1名</el-tag>
            <el-tag v-else-if="$index === 1" type="warning" size="small">第2名</el-tag>
            <el-tag v-else-if="$index === 2" type="success" size="small">第3名</el-tag>
            <span v-else>第{{ $index + 1 }}名</span>
          </template>
        </el-table-column>
        <el-table-column prop="student_name" label="姓名" min-width="150" />
        <el-table-column prop="total_score" label="总分" width="100" align="center">
          <template #default="{ row }">
            <span style="font-weight: bold; font-size: 16px; color: #409EFF">{{ row.total_score }}</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../utils/api'

const route = useRoute()
const router = useRouter()

const classId = route.params.classId
const publishId = route.params.examId // examId 实际就是 publish_id

const loading = ref(false)
const saving = ref(false)
const finishing = ref(false)
const paperInfo = ref({ title: '', total_score: 0, finished_at: null })
const questions = ref([])
const students = ref([])

// 计算表格数据（包含平均分一行）
const tableData = computed(() => {
  if (students.value.length === 0) return []

  const avgScores = {}
  let avgTotal = 0

  for (const q of questions.value) {
    let sum = 0
    for (const s of students.value) {
      sum += (s.scores[q.question_id] || 0)
    }
    avgScores[q.question_id] = sum / students.value.length
  }

  for (const s of students.value) {
    avgTotal += s.total_score
  }
  avgTotal = avgTotal / students.value.length

  const avgRow = {
    student_name: '平均分',
    scores: avgScores,
    total_score: avgTotal,
    isAverage: true
  }

  return [...students.value, avgRow]
})

// 计算排名（按总分降序）
const rankings = computed(() => {
  return [...students.value]
    .filter(s => s.total_score > 0)
    .sort((a, b) => b.total_score - a.total_score)
})

function updateTotal(row) {
  let total = 0
  for (const q of questions.value) {
    total += (row.scores[q.question_id] || 0)
  }
  row.total_score = total
}

function onAbsentChange(row) {
  if (row.absent) {
    // 标记为未参加，清空成绩
    for (const q of questions.value) {
      row.scores[q.question_id] = 0
    }
    row.total_score = 0
  }
}

async function loadData() {
  loading.value = true
  try {
    const res = await api.get(`/classes/${classId}/exams/${publishId}/scores`)
    paperInfo.value = res.paper
    questions.value = res.questions
    students.value = res.students.map(s => ({
      ...s,
      absent: false  // 初始化未参加标记
    }))
  } catch (error) {
    ElMessage.error('加载数据失败')
    goBack()
  } finally {
    loading.value = false
  }
}

async function saveScores() {
  saving.value = true
  try {
    for (const student of students.value) {
      const scores_data = questions.value.map(q => ({
        question_id: q.question_id,
        score: student.scores[q.question_id] || 0,
        max_score: q.max_score
      }))

      await api.post(`/papers/${paperInfo.value.id}/students/${student.student_id}/scores`, {
        scores: scores_data
      })
    }
    ElMessage.success('成绩保存成功')
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

async function finishScoring() {
  try {
    await ElMessageBox.confirm(
      '结束登记后将无法再修改成绩，确定要结束登记吗？',
      '确认结束登记',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }

  finishing.value = true
  try {
    const absentIds = students.value
      .filter(s => s.absent)
      .map(s => s.student_id)

    await api.post(`/papers/${paperInfo.value.id}/finish-scoring`, {
      publish_id: publishId,
      absent_student_ids: absentIds
    })
    paperInfo.value.finished_at = new Date().toISOString()
    ElMessage.success('登记已结束')
    // 结束登记后，返回到班级详情页面
    setTimeout(() => {
      goBack()
    }, 1500)
  } catch (error) {
    ElMessage.error('操作失败')
  } finally {
    finishing.value = false
  }
}

function goBack() {
  router.push(`/classes/${classId}`)
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.paper-score-page {
  padding: 20px;
}

.page-header {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
  gap: 10px;
}

.page-header h3 {
  font-size: 16px;
  color: #303133;
}

.card-header {
  font-weight: bold;
  color: #303133;
}
</style>
