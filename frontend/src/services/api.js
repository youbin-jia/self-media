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

// Workflow steps（video 含 LTX 侧车 / MoviePy 时可能极慢，由调用方加大 timeout）
export const executeStep = (projectId, stepName, data, axiosConfig = {}) =>
  api.post(`/projects/${projectId}/steps/${stepName}/execute`, data, { timeout: 180000, ...axiosConfig })
export const regenerateStep = (projectId, stepName, data, axiosConfig = {}) =>
  api.post(`/projects/${projectId}/steps/${stepName}/regenerate`, data, { timeout: 180000, ...axiosConfig })

/** 视频管线环境：LTX-2、Wan I2V 等（不含密钥） */
export const getVideoPipelineEnv = () => api.get('/video/pipeline-env')

/** 本机 CPU/内存/GPU 指标（视频页实时监控） */
export const getVideoHostMetrics = () => api.get('/video/host-metrics', { timeout: 8000 })

export default api
