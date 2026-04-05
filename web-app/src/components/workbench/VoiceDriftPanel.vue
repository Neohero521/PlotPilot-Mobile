<template>
  <div class="drift-panel">
    <div class="panel-header">
      <span class="panel-title">文风漂移监控</span>
      <n-button size="small" :loading="loading" @click="load">刷新</n-button>
    </div>

    <!-- 告警横幅 -->
    <n-alert
      v-if="report && report.drift_alert"
      type="warning"
      title="⚠️ 文风漂移告警"
      class="drift-alert"
    >
      最近 {{ report.alert_consecutive }} 章相似度均低于
      {{ (report.alert_threshold * 100).toFixed(0) }}%，
      建议回顾作者指纹或调整写作风格。
    </n-alert>

    <n-alert v-else-if="report && report.scores.length >= report.alert_consecutive" type="success" title="文风正常" class="drift-alert">
      近期文风与作者指纹匹配良好。
    </n-alert>

    <n-alert v-else-if="report && report.scores.length < 10" type="info" class="drift-alert">
      样本不足（需至少 10 个文风样本才能计算相似度）。请先在「采血」功能添加样本。
    </n-alert>

    <!-- 评分趋势表格 -->
    <n-data-table
      v-if="report && report.scores.length"
      :columns="columns"
      :data="report.scores.slice().reverse()"
      :max-height="320"
      size="small"
      striped
      class="score-table"
    />

    <n-empty v-else-if="!loading && report" description="暂无评分数据" size="small" />
    <n-spin v-if="loading" size="small" class="spin" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import { NTag, NProgress } from 'naive-ui'
import { voiceDriftApi, type DriftReportResponse } from '@/api/voiceDrift'

const props = defineProps<{ slug: string }>()

const loading = ref(false)
const report = ref<DriftReportResponse | null>(null)

async function load() {
  if (!props.slug) return
  loading.value = true
  try {
    report.value = await voiceDriftApi.getDriftReport(props.slug)
  } catch (e) {
    report.value = null
  } finally {
    loading.value = false
  }
}

const columns = [
  {
    title: '章节',
    key: 'chapter_number',
    width: 60,
  },
  {
    title: '相似度',
    key: 'similarity_score',
    width: 120,
    render(row: any) {
      const pct = Math.round(row.similarity_score * 100)
      const status = pct >= 75 ? 'success' : pct >= 50 ? 'warning' : 'error'
      return h(NProgress, {
        type: 'line',
        percentage: pct,
        status,
        indicatorPlacement: 'inside',
        height: 18,
      })
    },
  },
  {
    title: '形容词密度',
    key: 'adjective_density',
    render: (row: any) => `${(row.adjective_density * 100).toFixed(2)}%`,
    width: 100,
  },
  {
    title: '均句长',
    key: 'avg_sentence_length',
    render: (row: any) => `${row.avg_sentence_length.toFixed(1)}字`,
    width: 80,
  },
  {
    title: '状态',
    key: 'status',
    width: 70,
    render(row: any) {
      const ok = row.similarity_score >= 0.75
      return h(NTag, { type: ok ? 'success' : 'warning', size: 'small' }, () => ok ? '正常' : '偏离')
    },
  },
  {
    title: '计算时间',
    key: 'computed_at',
    render: (row: any) => row.computed_at?.slice(0, 16) ?? '-',
  },
]

onMounted(load)
</script>

<style scoped>
.drift-panel {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.panel-title {
  font-weight: 600;
  font-size: 14px;
}
.drift-alert {
  margin: 0;
}
.score-table {
  border-radius: 6px;
  overflow: hidden;
}
.spin {
  align-self: center;
  margin-top: 20px;
}
</style>
