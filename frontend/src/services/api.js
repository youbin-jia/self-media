import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000
})

// Topics
export const getTopics = () => api.get('/topics')
export const createTopic = (data) => api.post('/topics', data)
export const updateTopic = (id, data) => api.put(`/topics/${id}`, data)
export const deleteTopic = (id) => api.delete(`/topics/${id}`)

// Projects
export const getProjects = () => api.get('/projects')
export const getProject = (id) => api.get(`/projects/${id}`)
export const createProject = (data) => api.post('/projects', data)
export const updateProject = (id, data) => api.put(`/projects/${id}`, data)
export const deleteProject = (id) => api.delete(`/projects/${id}`)

// Workflow steps
export const executeStep = (projectId, stepName) => api.post(`/projects/${projectId}/steps/${stepName}/execute`)
export const regenerateStep = (projectId, stepName) => api.post(`/projects/${projectId}/steps/${stepName}/regenerate`)

export default api
