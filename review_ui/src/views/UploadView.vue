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

          <!-- Large File Warning -->
          <div class="large-file-warning" v-if="selectedFile && selectedFile.size > 10 * 1024 * 1024">
            <p><strong>⚠️ Large file detected!</strong></p>
            <p>Files over 10 MB may take 10+ minutes to process. Consider splitting your PDF into smaller files for faster processing.</p>
            <p class="warning-detail">Upload will continue, but you can navigate away while it processes in the background.</p>
          </div>
        </div>

        <!-- Upload Progress -->
        <div class="upload-progress" v-if="uploading || processing">
          <div v-if="uploading" class="progress-stage">
            <ProgressBar :value="uploadProgress" :showValue="true" />
            <p class="progress-text">{{ uploadProgress }}% uploaded ({{ formatFileSize(bytesUploaded) }} / {{ formatFileSize(totalBytes) }})</p>
          </div>

          <div v-if="processing" class="processing-stages">
            <div class="stage" :class="{ 'active': currentStage === 'uploading' }">
              <i class="pi" :class="currentStage === 'uploading' ? 'pi-spin pi-spinner' : 'pi-check'"></i>
              <span>Uploading document</span>
            </div>
            <div class="stage" :class="{ 'active': currentStage === 'extracting', 'completed': stagesCompleted.uploading }">
              <i class="pi" :class="currentStage === 'extracting' ? 'pi-spin pi-spinner' : stagesCompleted.uploading ? 'pi-check' : 'pi-circle'"></i>
              <span>Extracting pages from PDF</span>
            </div>
            <div class="stage" :class="{ 'active': currentStage === 'ocr', 'completed': stagesCompleted.extracting }">
              <i class="pi" :class="currentStage === 'ocr' ? 'pi-spin pi-spinner' : stagesCompleted.extracting ? 'pi-check' : 'pi-circle'"></i>
              <span>Running OCR ({{ ocrProgress }}%)</span>
            </div>
            <div class="stage" :class="{ 'active': currentStage === 'analyzing', 'completed': stagesCompleted.ocr }">
              <i class="pi" :class="currentStage === 'analyzing' ? 'pi-spin pi-spinner' : stagesCompleted.ocr ? 'pi-check' : 'pi-circle'"></i>
              <span>Analyzing text quality</span>
            </div>
            <div class="stage" :class="{ 'completed': stagesCompleted.analyzing }">
              <i class="pi" :class="stagesCompleted.analyzing ? 'pi-check' : 'pi-circle'"></i>
              <span>Ready for review</span>
            </div>
          </div>
        </div>

        <div class="upload-actions">
          <Button label="Upload & Process" icon="pi pi-upload"
                  :disabled="!selectedFile || uploading || processing"
                  :loading="uploading || processing"
                  @click="uploadFile"
                  severity="success" />
        </div>

        <!-- Time Estimate -->
        <div class="time-estimate" v-if="selectedFile">
          <p><strong>⏱️ Estimated processing time:</strong> {{ estimateTime() }}</p>
          <p class="estimate-detail">Based on file size ({{ formatFileSize(selectedFile.size) }})</p>
        </div>

        <div class="upload-info">
          <p><strong>What happens next:</strong></p>
          <ol>
            <li>Document is uploaded and queued for OCR processing</li>
            <li>Tesseract OCR extracts text with confidence scores</li>
            <li>Text quality is analyzed</li>
            <li>Review queue is created with detected errors</li>
            <li>You'll review each error and approve or correct the text</li>
          </ol>
          <p class="note">💡 Processing happens in the background - you can navigate away and come back!</p>
        </div>
      </template>
    </Card>
  </div>
</template>

<script setup>
import { ref, onBeforeUnmount, watch } from 'vue'
import { useRouter, onBeforeRouteLeave } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import { useDocumentsStore } from '../stores/documents'

const router = useRouter()
const toast = useToast()
const documentsStore = useDocumentsStore()

const isDragOver = ref(false)
const selectedFile = ref(null)
const uploading = ref(false)
const processing = ref(false)
const fileInput = ref(null)

// Upload progress
const uploadProgress = ref(0)
const bytesUploaded = ref(0)
const totalBytes = ref(0)

// Processing stages
const currentStage = ref('')
const ocrProgress = ref(0)
const stagesCompleted = ref({
  uploading: false,
  extracting: false,
  ocr: false,
  analyzing: false
})

// Polling interval
let pollInterval = null

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
  currentStage.value = 'uploading'
  totalBytes.value = selectedFile.value.size

  // Track upload progress with XMLHttpRequest
  const result = await documentsStore.uploadDocumentWithProgress(
    selectedFile.value,
    (progress) => {
      uploadProgress.value = progress.percent
      bytesUploaded.value = progress.loaded
    }
  )

  uploading.value = false
  processing.value = true
  stagesCompleted.value.uploading = true

  // Poll for processing status
  pollDocumentStatus(result.document_id)
}

const pollDocumentStatus = async (documentId) => {
  pollInterval = setInterval(async () => {
    try {
      const doc = await documentsStore.getDocument(documentId)

      // Update stages based on document status
      if (doc.status === 'processing') {
        currentStage.value = 'extracting'
        if (doc.processed_pages > 0) {
          currentStage.value = 'ocr'
          ocrProgress.value = doc.progress_percentage || 0
        }
      } else if (doc.status === 'ready' || doc.status === 'completed') {
        currentStage.value = 'analyzing'
        stagesCompleted.value = {
          uploading: true,
          extracting: true,
          ocr: true,
          analyzing: true
        }

        // Processing complete!
        clearInterval(pollInterval)
        processing.value = false

        toast.add({
          severity: 'success',
          summary: 'Processing Complete!',
          detail: `"${doc.filename}" is ready for review`,
          life: 5000
        })

        // Navigate to review page
        setTimeout(() => {
          router.push(`/documents/${documentId}`)
        }, 1500)

      } else if (doc.status === 'error') {
        clearInterval(pollInterval)
        processing.value = false

        toast.add({
          severity: 'error',
          summary: 'Processing Failed',
          detail: 'There was an error processing your document'
        })
      }
    } catch (error) {
      console.error('Error polling document status:', error)
    }
  }, 2000) // Poll every 2 seconds
}

// Navigation guard
const beforeUnload = (e) => {
  if (uploading.value) {
    e.preventDefault()
    e.returnValue = ''
    return 'Upload is in progress. Are you sure you want to leave?'
  }
}

onBeforeUnmount(() => {
  if (pollInterval) {
    clearInterval(pollInterval)
  }
  window.removeEventListener('beforeunload', beforeUnload)
})

// Navigation guard for Vue Router
onBeforeRouteLeave((to, from, next) => {
  if (uploading.value) {
    const answer = confirm('Upload is in progress. Are you sure you want to leave? The upload will be cancelled.')
    if (answer) {
      next()
    } else {
      next(false)
    }
  } else {
    next()
  }
})

// Add navigation guard when uploading starts
const startUpload = () => {
  window.addEventListener('beforeunload', beforeUnload)
}

// Watch for uploading state
watch(uploading, (isUploading) => {
  if (isUploading) {
    startUpload()
  } else {
    window.removeEventListener('beforeunload', beforeUnload)
  }
})

const formatFileSize = (bytes) => {
  if (!bytes) return '0 B'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

// Estimate processing time based on file size
const estimateTime = () => {
  if (!selectedFile.value) return ''

  const sizeMB = selectedFile.value.size / (1024 * 1024)

  // Rough estimates based on Railway free tier performance
  let uploadMinutes = Math.ceil(sizeMB / 10) // ~10 MB/min upload
  let processingMinutes = Math.ceil(sizeMB / 2) // ~2 MB/min processing

  // Base time + file size factor
  let totalMinutes = uploadMinutes + processingMinutes + 2 // 2 min overhead

  if (totalMinutes < 5) {
    return '3-5 minutes'
  } else if (totalMinutes < 10) {
    return '5-10 minutes'
  } else if (totalMinutes < 20) {
    return '10-20 minutes'
  } else {
    return `${Math.ceil(totalMinutes / 5) * 5}-${Math.ceil((totalMinutes + 5) / 5) * 5} minutes`
  }
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

.upload-progress {
  margin-top: 1.5rem;
  padding: 1rem;
  background: #f8fafc;
  border-radius: 8px;
}

.progress-stage {
  margin-bottom: 1rem;
}

.progress-text {
  margin: 0.5rem 0 0;
  text-align: center;
  color: #64748b;
  font-size: 0.875rem;
}

.processing-stages {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.stage {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  border-radius: 6px;
  background: white;
  transition: all 0.3s;
}

.stage.active {
  background: #dbeafe;
  font-weight: 500;
}

.stage.completed {
  background: #dcfce7;
}

.stage i {
  width: 1.25rem;
  height: 1.25rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stage .pi-circle {
  color: #cbd5e1;
}

.stage .pi-check {
  color: #16a34a;
}

.stage .pi-spin {
  color: #2563eb;
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

.note {
  margin-top: 1rem;
  padding: 0.75rem;
  background: #e0f2fe;
  border-radius: 6px;
  font-size: 0.875rem;
  color: #0369a1;
}

.time-estimate {
  margin-top: 1.5rem;
  padding: 1rem;
  background: #fef9e7;
  border-left: 4px solid #f59e0b;
  border-radius: 6px;
}

.time-estimate p {
  margin: 0 0 0.5rem;
}

.time-estimate strong {
  color: #92400e;
}

.estimate-detail {
  font-size: 0.875rem;
  color: #78716c;
  margin: 0;
}
</style>
