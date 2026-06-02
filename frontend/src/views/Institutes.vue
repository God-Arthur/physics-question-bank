<template>
  <div class="institute-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>机构管理</span>
          <el-button type="primary" size="small" @click="showAddDialog">
            <el-icon><Plus /></el-icon>
            新建机构
          </el-button>
        </div>
      </template>
      
      <el-table :data="institutes" stripe border style="width: 100%">
        <el-table-column prop="code" label="机构代码" width="120" />
        <el-table-column prop="name" label="机构名称" />
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="showEditDialog(row)">编辑</el-button>
            <el-popconfirm title="确定删除该机构吗？" @confirm="deleteInstitute(row.id)">
              <template #reference>
                <el-button type="danger" link size="small">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <!-- 新建/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑机构' : '新建机构'" width="450px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="90px">
        <el-form-item label="机构名称" prop="name">
          <el-input v-model="form.name" placeholder="如：兰阶" />
        </el-form-item>
        <el-form-item label="机构代码" prop="code">
          <el-input v-model="form.code" placeholder="3位大写字母" maxlength="3" style="text-transform: uppercase" :disabled="isEdit" />
          <div style="font-size: 12px; color: #909399; margin-top: 4px">机构代码必须是3位大写字母，创建后不可修改</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../utils/api'

const institutes = ref([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const formRef = ref(null)

const form = reactive({
  id: null,
  name: '',
  code: ''
})

const rules = {
  name: [{ required: true, message: '请输入机构名称', trigger: 'blur' }],
  code: [
    { required: true, message: '请输入机构代码', trigger: 'blur' },
    { pattern: /^[A-Z]{3}$/, message: '必须是3位大写字母', trigger: 'blur' }
  ]
}

async function loadInstitutes() {
  try {
    const res = await api.get('/institutes/')
    institutes.value = res.institutes || []
  } catch (e) {
    // 错误已处理
  }
}

function showAddDialog() {
  isEdit.value = false
  form.id = null
  form.name = ''
  form.code = ''
  dialogVisible.value = true
}

function showEditDialog(row) {
  isEdit.value = true
  form.id = row.id
  form.name = row.name
  form.code = row.code
  dialogVisible.value = true
}

async function submitForm() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      if (isEdit.value) {
        await api.put(`/institutes/${form.id}`, { name: form.name })
        ElMessage.success('机构更新成功')
      } else {
        await api.post('/institutes/', { name: form.name, code: form.code.toUpperCase() })
        ElMessage.success('机构创建成功')
      }
      dialogVisible.value = false
      loadInstitutes()
    } catch (e) {
      // 错误已处理
    } finally {
      submitting.value = false
    }
  })
}

async function deleteInstitute(id) {
  try {
    await api.delete(`/institutes/${id}`)
    ElMessage.success('机构删除成功')
    loadInstitutes()
  } catch (e) {
    // 错误已处理
  }
}

onMounted(() => {
  loadInstitutes()
})
</script>

<style scoped>
.institute-page {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
