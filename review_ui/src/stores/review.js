import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { reviewsApi } from '../api'

export const useReviewStore = defineStore('review', () => {
  const currentError = ref(null)
  const summary = ref(null)
  const loading = ref(false)
  const submitting = ref(false)
  const error = ref(null)

  const fetchNextError = async (documentId) => {
    loading.value = true
    error.value = null
    try {
      currentError.value = await reviewsApi.getNextError(documentId)
      return currentError.value
    } catch (e) {
      if (e.response?.status === 404) {
        currentError.value = { status: 'complete' }
      } else {
        error.value = e.message
      }
    } finally {
      loading.value = false
    }
  }

  const fetchSummary = async (documentId) => {
    loading.value = true
    error.value = null
    try {
      summary.value = await reviewsApi.getSummary(documentId)
    } catch (e) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  const submitCorrection = async (correction) => {
    submitting.value = true
    error.value = null
    try {
      const result = await reviewsApi.submitCorrection(correction)
      currentError.value = null
      return result
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      submitting.value = false
    }
  }

  const isComplete = computed(() => {
    return currentError.value?.status === 'complete'
  })

  const completionPercentage = computed(() => {
    return summary.value?.completion_percentage || 0
  })

  return {
    currentError,
    summary,
    loading,
    submitting,
    error,
    fetchNextError,
    fetchSummary,
    submitCorrection,
    isComplete,
    completionPercentage
  }
})
