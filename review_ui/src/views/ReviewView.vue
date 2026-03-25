<template>
  <div class="review-view">
    <div v-if="!documentId" class="no-document">
      <Card>
        <template #content>
          <p>Select a document to review</p>
          <Button label="Browse Documents" icon="pi pi-list" @click="$router.push('/documents')" />
        </template>
      </Card>
    </div>

    <div v-else class="review-container">
      <!-- Document Header -->
      <Card class="doc-header">
        <template #content>
          <div class="header-content">
            <div>
              <h2>{{ currentDocument?.filename }}</h2>
              <div class="doc-stats">
                <Badge :value="`${Math.round(completionPercentage)}% Complete`" severity="info" />
                <span>{{ summary?.pending || 0 }} errors remaining</span>
              </div>
            </div>
            <div class="header-actions">
              <Button label="Export Text" icon="pi pi-download" text @click="exportText" />
              <Button label="Back to Documents" icon="pi pi-arrow-left" text @click="$router.push('/documents')" />
            </div>
          </div>
          <ProgressBar :value="completionPercentage" :showValue="true" />
        </template>
      </Card>

      <!-- Loading State -->
      <div v-if="reviewStore.loading" class="loading-state">
        <i class="pi pi-spin pi-spinner" style="font-size: 2rem;"></i>
        <p>Loading next error...</p>
      </div>

      <!-- Complete State -->
      <Card v-else-if="reviewStore.isComplete" class="complete-state">
        <template #content>
          <div class="complete-content">
            <i class="pi pi-check-circle" style="font-size: 4rem; color: #22c55e;"></i>
            <h2>All Errors Reviewed!</h2>
            <p>You've reviewed all potential OCR errors in this document.</p>
            <div class="complete-actions">
              <Button label="Export Corrected Text" icon="pi pi-download" severity="success" @click="exportText" />
              <Button label="View Statistics" icon="pi pi-chart-bar" @click="showStats = true" />
              <Button label="Back to Documents" icon="pi pi-list" @click="$router.push('/documents')" />
            </div>
          </div>
        </template>
      </Card>

      <!-- Review Interface -->
      <div v-else-if="currentError" class="review-interface">
        <div class="view-toggle">
          <Button :class="{ active: viewMode === 'split' }" label="Split View" @click="viewMode = 'split'" />
          <Button :class="{ active: viewMode === 'overlay' }" label="Overlay Mode" @click="viewMode = 'overlay'" />
        </div>

        <!-- Split View -->
        <div v-if="viewMode === 'split'" class="split-view">
          <!-- Left: Image Context -->
          <div class="image-panel">
            <Panel header="Image Context" toggleable>
              <div class="image-container">
                <div class="error-highlight">
                  <span class="error-word">{{ currentError.original_word }}</span>
                  <Badge :value="`${Math.round(currentError.confidence * 100)}% confidence`"
                         :severity="getConfidenceSeverity(currentError.confidence)" />
                </div>
                <p class="context-text">{{ currentError.context }}</p>
                <div class="bbox-info" v-if="currentError.bbox">
                  <small>Location: {{ currentError.bbox.join(', ') }}</small>
                </div>
              </div>
            </Panel>
          </div>

          <!-- Right: Correction Panel -->
          <div class="correction-panel">
            <Panel header="Review & Correct">
              <div class="correction-content">
                <div class="error-display">
                  <label>OCR Output:</label>
                  <div class="error-word-display">{{ currentError.original_word }}</div>
                  <Badge :value="getConfidenceLabel(currentError.confidence)"
                         :severity="getConfidenceSeverity(currentError.confidence)" />
                </div>

                <div class="suggestions">
                  <label>Suggested Corrections:</label>
                  <div v-if="currentError.suggestions && currentError.suggestions.length > 0">
                    <div v-for="(suggestion, idx) in currentError.suggestions" :key="idx" class="suggestion-item">
                      <RadioButton :modelValue="selectedSuggestion" :value="idx" @update:modelValue="selectedSuggestion = idx" />
                      <span class="suggestion-text">{{ suggestion.text || suggestion }}</span>
                      <Badge v-if="suggestion.score" :value="`${Math.round(suggestion.score * 100)}% match`" />
                    </div>
                  </div>
                  <p v-else class="no-suggestions">No suggestions available</p>
                </div>

                <div class="custom-input">
                  <label>Or enter custom correction:</label>
                  <InputText v-model="customCorrection" placeholder="Type correction..." />
                </div>

                <div class="review-actions">
                  <Button label="Skip" icon="pi pi-forward" severity="secondary" @click="skipError" />
                  <Button label="Approve Original" icon="pi pi-check" severity="success" @click="approveOriginal" />
                  <Button label="Apply Correction" icon="pi pi-pencil" @click="applyCorrection"
                          :disabled="selectedSuggestion === null && !customCorrection" />
                </div>
              </div>
            </Panel>
          </div>
        </div>

        <!-- Overlay Mode -->
        <div v-else class="overlay-view">
          <Panel header="Overlay Review Mode">
            <div class="overlay-content">
              <div class="overlay-image">
                <div class="overlay-text">
                  <span class="overlay-error">{{ currentError.original_word }}</span>
                </div>
                <p class="overlay-context">{{ currentError.context }}</p>
              </div>

              <div class="overlay-controls">
                <div class="suggestions-quick">
                  <Button v-for="(suggestion, idx) in (currentError.suggestions || []).slice(0, 3)"
                          :key="idx"
                          :label="suggestion.text || suggestion"
                          @click="quickApply(idx)" />
                  <Button label="Original" severity="secondary" @click="approveOriginal" />
                  <Button label="Skip" text @click="skipError" />
                </div>
              </div>
            </div>
          </Panel>
        </div>
      </div>
    </div>

    <!-- Statistics Dialog -->
    <Dialog v-model:visible="showStats" header="Document Statistics" modal style="width: 500px">
      <div v-if="statistics" class="stats-content">
        <div class="stat-item">
          <span class="stat-label">Total Errors:</span>
          <span class="stat-value">{{ statistics.error_statistics.total_errors }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">Corrected:</span>
          <span class="stat-value">{{ statistics.error_statistics.corrected }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">Approved:</span>
          <span class="stat-value">{{ statistics.error_statistics.approved }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">Skipped:</span>
          <span class="stat-value">{{ statistics.error_statistics.skipped }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">Average Confidence:</span>
          <span class="stat-value">{{ Math.round(statistics.confidence_statistics.average_confidence * 100) }}%</span>
        </div>
      </div>
      <template #footer>
        <Button label="Close" @click="showStats = false" />
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import { useDocumentsStore } from '../stores/documents'
import { useReviewStore } from '../stores/review'
import { exportApi } from '../api'

const route = useRoute()
const toast = useToast()
const documentsStore = useDocumentsStore()
const reviewStore = useReviewStore()

const documentId = computed(() => route.params.documentId)
const currentDocument = computed(() => documentsStore.currentDocument)
const currentError = computed(() => reviewStore.currentError)
const summary = computed(() => reviewStore.summary)
const completionPercentage = computed(() => reviewStore.completionPercentage)

const viewMode = ref('split')
const selectedSuggestion = ref(null)
const customCorrection = ref('')
const showStats = ref(false)
const statistics = ref(null)

onMounted(async () => {
  if (documentId.value) {
    await documentsStore.fetchDocument(documentId.value)
    await reviewStore.fetchSummary(documentId.value)
    await reviewStore.fetchNextError(documentId.value)
  }
})

const getConfidenceSeverity = (confidence) => {
  if (confidence >= 0.85) return 'success'
  if (confidence >= 0.70) return 'warn'
  return 'danger'
}

const getConfidenceLabel = (confidence) => {
  if (confidence >= 0.85) return 'High confidence'
  if (confidence >= 0.70) return 'Medium confidence'
  return 'Low confidence'
}

const skipError = async () => {
  await reviewStore.submitCorrection({
    error_id: currentError.value.error_id,
    skipped: true
  })
  toast.add({ severity: 'info', summary: 'Skipped', detail: 'Error skipped' })
  await nextError()
}

const approveOriginal = async () => {
  await reviewStore.submitCorrection({
    error_id: currentError.value.error_id,
    skipped: false
  })
  toast.add({ severity: 'success', summary: 'Approved', detail: 'Original text approved' })
  await nextError()
}

const applyCorrection = async () => {
  const correction = {
    error_id: currentError.value.error_id,
    selected_correction: selectedSuggestion.value,
    custom_correction: customCorrection.value || null,
    skipped: false
  }

  await reviewStore.submitCorrection(correction)
  toast.add({ severity: 'success', summary: 'Corrected', detail: 'Correction applied' })

  selectedSuggestion.value = null
  customCorrection.value = ''
  await nextError()
}

const quickApply = async (index) => {
  selectedSuggestion.value = index
  await applyCorrection()
}

const nextError = async () => {
  await reviewStore.fetchNextError(documentId.value)
  await reviewStore.fetchSummary(documentId.value)
}

const exportText = async () => {
  try {
    const data = await exportApi.getText(documentId.value)
    const blob = new Blob([data.text], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${currentDocument.value?.filename}_corrected.txt`
    a.click()
    toast.add({ severity: 'success', summary: 'Exported', detail: 'Text exported successfully' })
  } catch (error) {
    toast.add({ severity: 'error', summary: 'Export Failed', detail: error.message })
  }
}
</script>

<style scoped>
.review-view {
  max-width: 1400px;
  margin: 0 auto;
}

.no-document {
  text-align: center;
  padding: 3rem;
}

.doc-header {
  margin-bottom: 1.5rem;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.doc-stats {
  display: flex;
  gap: 1rem;
  align-items: center;
  margin-top: 0.5rem;
  color: #64748b;
}

.header-actions {
  display: flex;
  gap: 0.5rem;
}

.loading-state {
  text-align: center;
  padding: 3rem;
  color: #64748b;
}

.complete-state {
  text-align: center;
  max-width: 600px;
  margin: 2rem auto;
}

.complete-content h2 {
  margin: 1rem 0;
}

.complete-actions {
  display: flex;
  gap: 1rem;
  justify-content: center;
  margin-top: 2rem;
}

.view-toggle {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
  justify-content: center;
}

.view-toggle button.active {
  background: #1e3a5f;
  color: white;
}

.split-view {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
}

.image-panel .image-container {
  padding: 1rem;
}

.error-highlight {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
}

.error-word {
  font-size: 2rem;
  font-weight: bold;
  color: #dc2626;
}

.context-text {
  font-size: 1.125rem;
  line-height: 1.8;
  color: #374151;
}

.bbox-info {
  margin-top: 1rem;
  color: #94a3b8;
}

.correction-panel .correction-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.error-display {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.error-word-display {
  font-size: 1.5rem;
  font-weight: 500;
  color: #dc2626;
}

.suggestions label,
.custom-input label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.suggestion-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  margin-bottom: 0.5rem;
  cursor: pointer;
  transition: background 0.2s;
}

.suggestion-item:hover {
  background: #f9fafb;
}

.suggestion-text {
  flex: 1;
  font-size: 1.125rem;
}

.no-suggestions {
  color: #94a3b8;
  font-style: italic;
}

.custom-input InputText {
  width: 100%;
}

.review-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 1rem;
}

.overlay-view {
  max-width: 900px;
  margin: 0 auto;
}

.overlay-content {
  text-align: center;
}

.overlay-image {
  background: #f8fafc;
  padding: 3rem;
  border-radius: 8px;
  margin-bottom: 1.5rem;
  position: relative;
}

.overlay-text {
  font-size: 2.5rem;
  margin-bottom: 1rem;
}

.overlay-error {
  background: #fef2f2;
  color: #dc2626;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  font-weight: bold;
}

.overlay-context {
  font-size: 1.25rem;
  line-height: 2;
  color: #374151;
}

.suggestions-quick {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  justify-content: center;
}

.stats-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  padding: 0.75rem 0;
  border-bottom: 1px solid #e5e7eb;
}

.stat-label {
  color: #64748b;
}

.stat-value {
  font-weight: 600;
}
</style>
