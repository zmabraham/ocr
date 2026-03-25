<template>
  <div class="upload-view">
  <Card>
    <template #title>Upload Document for OCR Processing</template>
    <template #content>
      <div class="upload-area" :class="{ 'drag-over': isDragOver }"
           @drop.prevent="handleDrop"
           @dragover.prevent="isDragOver = true"
           @dragleave.prevent="isDragOver = false">

        <input ref="fileInput" type="file" accept=".pdf" @change="handleFileSelect" hidden>

        <div class="upload-prompt" v-if="!selectedFile">
          <i class="pi pi-file-pdf" style="font-size: 3rem; color: #64748b;"></i>
          <p>Drag & drop a PDF file here, or click to browse</p>
          <p class="upload-hint">Supports PDF files with Hebrew, Yiddish, or Aramaic text</p>
          <Button label="Select File" @click="$refs.fileInput.click()" />
        </div>

        <div class="file-selected" v-else>
          <i class="pi pi-file-pdf" style="font-size: 2rem; color: #1e3a5f;"></i>
          <span class="file-name">{{ selectedFile.name }}</span>
          <span class="file-size">{{ formatFileSize(selectedFile.size) }}</span>
          <Button label="Remove" icon="pi pi-times" severity="danger" text @click="selectedFile = null" />
        </div>
      </div>

      <div class="upload-actions">
        <Button label="Upload & Process" icon="pi pi-upload"
                :disabled="!selectedFile || uploading"
                :loading="uploading"
                @click="uploadFile"
                severity="success" />
      </div>

      <div class="upload-info">
        <p><strong>What happens next:</strong></p>
        <ol>
          <li>Document is uploaded and queued for OCR processing</li>
          <li>Tesseract OCR extracts text with confidence scores</li>
          <li>DictaBERT analyzes text and detects potential errors</li>
          <li>Review queue is created with suggested corrections</li>
          <li>You'll review each error and approve or correct the text</li>
        </ol>
      </div>
    </template>
  </Card>
</div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import { useDocumentsStore } from '../stores/documents'

const router = useRouter()
const toast = useToast()
const documentsStore = useDocumentsStore()

const isDragOver = ref(false)
const selectedFile = ref(null)
const uploading = ref(false)
const fileInput = ref(null)

const handleDrop = (e) => {
  isDragOver.value = false
  const file = e.dataTransfer.files[0]
  if (file && file.type === 'application/pdf') {
    selectedFile.value = file
  } else {
    toast.add({
      severity: 'warn',
      summary: 'Invalid File',
      detail: 'Please upload a PDF file'
    })
  }
}

const handleFileSelect = (e) => {
  const file = e.target.files[0]
  if (file) {
    selectedFile.value = file
  }
}

const uploadFile = async () => {
  if (!selectedFile.value) return

  uploading.value = true
  try {
    const result = await documentsStore.uploadDocument(selectedFile.value)
    toast.add({
      severity: 'success',
      summary: 'Upload Successful',
      detail: `Document "${result.filename}" is being processed`
    })
    router.push(`/review/${result.document_id}`)
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Upload Failed',
      detail: error.message || 'Failed to upload document'
    })
  } finally {
    uploading.value = false
  }
}

const formatFileSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}
</script>

<style scoped>
.upload-view {
  max-width: 800px;
  margin: 0 auto;
}

.upload-area {
  border: 2px dashed #cbd5e1;
  border-radius: 8px;
  padding: 3rem;
  text-align: center;
  transition: all 0.3s;
  cursor: pointer;
}

.upload-area:hover,
.upload-area.drag-over {
  border-color: #1e3a5f;
  background: #f1f5f9;
}

.upload-prompt p {
  margin: 1rem 0 0.5rem;
  color: #475569;
}

.upload-hint {
  font-size: 0.875rem;
  color: #94a3b8;
}

.file-selected {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  background: #f8fafc;
  border-radius: 8px;
}

.file-name {
  font-weight: 500;
  flex: 1;
}

.file-size {
  color: #64748b;
  font-size: 0.875rem;
}

.upload-actions {
  margin-top: 1.5rem;
  text-align: center;
}

.upload-info {
  margin-top: 2rem;
  padding: 1rem;
  background: #fef3c7;
  border-radius: 8px;
}

.upload-info p {
  margin: 0 0 0.5rem;
}

.upload-info ol {
  margin: 0;
  padding-left: 1.5rem;
}

.upload-info li {
  margin-bottom: 0.25rem;
}
</style>
