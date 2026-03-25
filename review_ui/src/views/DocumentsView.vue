<template>
  <div class="documents-view">
  <Card>
    <template #title>Documents</template>
    <template #content>
      <div v-if="documentsStore.loading" class="loading">
        <p>Loading documents...</p>
      </div>

      <div v-else-if="documentsStore.documents.length === 0" class="empty-state">
        <i class="pi pi-folder-open" style="font-size: 3rem; color: #cbd5e1;"></i>
        <p>No documents yet. Upload your first PDF to get started.</p>
        <Button label="Upload Document" icon="pi pi-plus" @click="$router.push('/')" />
      </div>

      <div v-else class="documents-list">
        <div v-for="doc in documentsByStatus" :key="doc.id"
             class="document-card"
             @click="openDocument(doc)">

          <div class="doc-header">
            <i class="pi pi-file-pdf"></i>
            <span class="doc-filename">{{ doc.filename }}</span>
            <Badge :value="doc.status" :severity="getStatusSeverity(doc.status)" />
          </div>

          <div class="doc-info">
            <span>{{ doc.total_pages || '?' }} pages</span>
            <span>Uploaded: {{ formatDate(doc.upload_date) }}</span>
          </div>

          <ProgressBar v-if="doc.status === 'processing'"
                      :value="doc.progress_percentage"
                      :showValue="true"
                      class="doc-progress" />

          <div class="doc-actions">
            <Button v-if="doc.status === 'completed'" label="Review" icon="pi pi-eye" size="small" />
            <Button v-if="doc.status === 'ready'" label="Start Review" icon="pi pi-play" size="small" />
            <Button label="Delete" icon="pi pi-trash" severity="danger" text size="small"
                   @click.stop="confirmDelete(doc)" />
          </div>
        </div>
      </div>
    </template>
  </Card>
</div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { useDocumentsStore } from '../stores/documents'

const router = useRouter()
const confirm = useConfirm()
const toast = useToast()
const documentsStore = useDocumentsStore()

const documentsByStatus = computed(() => {
  return [...documentsStore.documents].sort((a, b) => {
    const statusOrder = { completed: 0, ready: 1, processing: 2, pending: 3 }
    return statusOrder[a.status] - statusOrder[b.status]
  })
})

onMounted(() => {
  documentsStore.fetchDocuments()
})

const openDocument = (doc) => {
  if (doc.status === 'completed' || doc.status === 'ready') {
    router.push(`/review/${doc.id}`)
  }
}

const confirmDelete = (doc) => {
  confirm.require({
    message: `Are you sure you want to delete "${doc.filename}"?`,
    header: 'Confirm Delete',
    accept: async () => {
      await documentsStore.deleteDocument(doc.id)
      toast.add({
        severity: 'success',
        summary: 'Deleted',
        detail: 'Document has been deleted'
      })
    }
  })
}

const getStatusSeverity = (status) => {
  const severities = {
    completed: 'success',
    ready: 'info',
    processing: 'warn',
    pending: 'secondary',
    error: 'danger'
  }
  return severities[status] || 'secondary'
}

const formatDate = (dateStr) => {
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}
</script>

<style scoped>
.documents-view {
  max-width: 1200px;
  margin: 0 auto;
}

.loading,
.empty-state {
  text-align: center;
  padding: 3rem;
  color: #64748b;
}

.empty-state p {
  margin: 1rem 0;
}

.documents-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1rem;
}

.document-card {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 1rem;
  cursor: pointer;
  transition: all 0.2s;
}

.document-card:hover {
  border-color: #1e3a5f;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.doc-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.doc-header i {
  color: #dc2626;
  font-size: 1.25rem;
}

.doc-filename {
  flex: 1;
  font-weight: 500;
}

.doc-info {
  display: flex;
  gap: 1rem;
  font-size: 0.875rem;
  color: #64748b;
  margin-bottom: 0.5rem;
}

.doc-progress {
  margin: 0.5rem 0;
}

.doc-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.5rem;
}
</style>
