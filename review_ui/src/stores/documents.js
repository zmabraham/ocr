import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { documentsApi } from '../api'

export const useDocumentsStore = defineStore('documents', () => {
  const documents = ref([])
  const currentDocument = ref(null)
  const loading = ref(false)
  const error = ref(null)

  const uploadDocument = async (file) => {
    loading.value = true
    error.value = null
    try {
      const result = await documentsApi.upload(file)
      await fetchDocuments()
      return result
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  // Upload with progress tracking
  const uploadDocumentWithProgress = async (file, onProgress) => {
    loading.value = true
    error.value = null
    try {
      const result = await documentsApi.uploadWithProgress(file, onProgress)
      return result
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  const fetchDocuments = async () => {
    loading.value = true
    error.value = null
    try {
      documents.value = await documentsApi.list()
    } catch (e) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  const fetchDocument = async (documentId) => {
    loading.value = true
    error.value = null
    try {
      currentDocument.value = await documentsApi.get(documentId)
      return currentDocument.value
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  const deleteDocument = async (documentId) => {
    loading.value = true
    error.value = null
    try {
      await documentsApi.delete(documentId)
      documents.value = documents.value.filter(d => d.id !== documentId)
    } catch (e) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  const getByStatus = (status) => {
    return computed(() =>
      documents.value.filter(d => d.status === status)
    )
  }

  return {
    documents,
    currentDocument,
    loading,
    error,
    uploadDocument,
    uploadDocumentWithProgress,
    fetchDocuments,
    fetchDocument,
    deleteDocument,
    getByStatus
  }
})
