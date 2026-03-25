import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
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
