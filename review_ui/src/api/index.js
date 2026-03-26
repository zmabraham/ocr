import axios from 'axios'

// Use Railway backend in production, localhost in development
const baseURL = import.meta.env.PROD
  ? 'https://ocr-production-e0be.up.railway.app/api'
  : '/api'

const api = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json'
  }
})

export const documentsApi = {
  upload: async (file) => {
    const formData = new FormData()
    formData.append('file', file)
    const response = await api.post('/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    return response.data
  },

  // Upload with progress tracking using XMLHttpRequest
  uploadWithProgress: (file, onProgress) => {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest()
      const formData = new FormData()
      formData.append('file', file)

      // Track upload progress
      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
          const percent = Math.round((e.loaded / e.total) * 100)
          onProgress({
            percent,
            loaded: e.loaded,
            total: e.total
          })
        }
      })

      // Handle completion
      xhr.addEventListener('load', () => {
        if (xhr.status === 200) {
          const response = JSON.parse(xhr.responseText)
          resolve(response)
        } else {
          reject(new Error(`Upload failed with status ${xhr.status}`))
        }
      })

      // Handle errors
      xhr.addEventListener('error', () => {
        reject(new Error('Upload failed - network error'))
      })

      xhr.addEventListener('abort', () => {
        reject(new Error('Upload aborted'))
      })

      // Open and send request
      xhr.open('POST', `${baseURL}/documents/upload`)
      xhr.send(formData)
    })
  },

  get: async (documentId) => {
    const response = await api.get(`/documents/${documentId}`)
    return response.data
  },

  list: async (params = {}) => {
    const response = await api.get('/documents/', { params })
    return response.data
  },

  delete: async (documentId) => {
    const response = await api.delete(`/documents/${documentId}`)
    return response.data
  }
}

export const reviewsApi = {
  getNextError: async (documentId) => {
    const response = await api.get(`/reviews/document/${documentId}/next-error`)
    return response.data
  },

  getSummary: async (documentId) => {
    const response = await api.get(`/reviews/document/${documentId}/summary`)
    return response.data
  },

  submitCorrection: async (correction) => {
    const response = await api.post('/reviews/submit', correction)
    return response.data
  },

  getDocumentErrors: async (documentId, status = null) => {
    const params = status ? { status } : {}
    const response = await api.get(`/reviews/document/${documentId}/errors`, { params })
    return response.data
  },

  getPending: async (documentId = null) => {
    const params = documentId ? { document_id: documentId } : {}
    const response = await api.get('/reviews/pending', { params })
    return response.data
  }
}

export const exportApi = {
  getText: async (documentId) => {
    const response = await api.get(`/export/document/${documentId}/text`)
    return response.data
  },

  downloadText: async (documentId) => {
    const response = await api.get(`/export/document/${documentId}/download`, {
      responseType: 'blob'
    })
    return response.data
  },

  getCorrectionsLog: async (documentId) => {
    const response = await api.get(`/export/document/${documentId}/corrections-log`)
    return response.data
  },

  getStatistics: async (documentId) => {
    const response = await api.get(`/export/document/${documentId}/statistics`)
    return response.data
  }
}
