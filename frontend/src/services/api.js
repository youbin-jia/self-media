import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000
})

// Topics
export const getTopics = (params) => api.get('/topics/list', { params })
export const refreshTopics = () => api.post('/topics/refresh')

// Projects
export const getProjects = () => api.get('/projects/')
export const getProject = (id) => api.get(`/projects/${id}`)
export const createProject = (data) => api.post('/projects/', data)
export const updateProject = (id, data) => api.put(`/projects/${id}`, data)
export const deleteProject = (id) => api.delete(`/projects/${id}`)
export const updateProjectScript = (projectId, data) => api.put(`/scripts/project/${projectId}`, data)
export const getProjectScript = (projectId) => api.get(`/scripts/project/${projectId}`)
export const getProjectScriptHistory = (projectId, limit = 20) =>
  api.get(`/scripts/project/${projectId}/history`, { params: { limit } })
export const rollbackProjectScript = (projectId, historyId) =>
  api.post(`/scripts/project/${projectId}/rollback/${historyId}`)
export const deleteProjectScriptHistory = (projectId, historyId) =>
  api.delete(`/scripts/project/${projectId}/history/${historyId}`, { params: { confirm: true } })
export const clearProjectScriptHistory = (projectId) =>
  api.delete(`/scripts/project/${projectId}/history`, { params: { confirm: true } })
export const aiReviseProjectScript = (projectId, data) =>
  api.post(`/scripts/project/${projectId}/ai-revise`, data, { timeout: 180000 })

// Workflow steps
export const executeStep = (projectId, stepName, data) =>
  api.post(`/projects/${projectId}/steps/${stepName}/execute`, data, { timeout: 180000 })
export const regenerateStep = (projectId, stepName, data) =>
  api.post(`/projects/${projectId}/steps/${stepName}/regenerate`, data, { timeout: 180000 })

export default api
