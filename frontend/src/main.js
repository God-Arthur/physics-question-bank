import { createApp } from 'vue'
import { createPinia } from 'pinia'
import 'katex/dist/katex.min.css'
import {
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  ArrowUp,
  Calendar,
  Check,
  Clock,
  CopyDocument,
  Crop,
  Delete,
  Document,
  DocumentChecked,
  Loading,
  Message,
  Notebook,
  OfficeBuilding,
  Plus,
  Refresh,
  School,
  Setting,
  Star,
  Tickets,
  Upload,
  User,
  UserFilled,
  ZoomIn
} from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'
import './style.css'

const app = createApp(App)

const icons = {
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  ArrowUp,
  Calendar,
  Check,
  Clock,
  CopyDocument,
  Crop,
  Delete,
  Document,
  DocumentChecked,
  Loading,
  Message,
  Notebook,
  OfficeBuilding,
  Plus,
  Refresh,
  School,
  Setting,
  Star,
  Tickets,
  Upload,
  User,
  UserFilled,
  ZoomIn
}

Object.entries(icons).forEach(([name, component]) => {
  app.component(name, component)
})

app.use(createPinia())
app.use(router)

app.mount('#app')
