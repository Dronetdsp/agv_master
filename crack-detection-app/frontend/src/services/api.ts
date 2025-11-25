/**
 * API service layer using axios
 * Type-safe API calls to FastAPI backend
 */
import axios from 'axios';
import type {
  InferenceConfig,
  InferenceRequest,
  InferenceResponse,
  UserPreferences,
  UploadResponse,
} from '@/types/api';

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for logging
api.interceptors.request.use((config) => {
  console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
  return config;
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export const apiService = {
  // Health check
  async healthCheck() {
    const { data } = await api.get('/health');
    return data;
  },

  // Upload images
  async uploadImages(buildingName: string, files: File[]): Promise<UploadResponse> {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });

    const { data } = await api.post<UploadResponse>(
      `/inference/upload?building_name=${encodeURIComponent(buildingName)}`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );

    return data;
  },

  // Start inference
  async startInference(request: InferenceRequest): Promise<InferenceResponse> {
    const { data } = await api.post<InferenceResponse>('/inference/start', request);
    return data;
  },

  // Get task status
  async getTaskStatus(taskId: string): Promise<InferenceResponse> {
    const { data } = await api.get<InferenceResponse>(`/inference/status/${taskId}`);
    return data;
  },

  // List all tasks
  async listTasks() {
    const { data } = await api.get('/inference/tasks');
    return data;
  },

  // Delete task
  async deleteTask(taskId: string) {
    const { data } = await api.delete(`/inference/tasks/${taskId}`);
    return data;
  },

  // Download file
  getDownloadUrl(buildingName: string, filename: string): string {
    return `/api/v1/inference/download/${encodeURIComponent(buildingName)}/${filename}`;
  },

  // Preferences
  async getPreferences(userId: string = 'default'): Promise<UserPreferences> {
    const { data } = await api.get<UserPreferences>(`/preferences/?user_id=${userId}`);
    return data;
  },

  async savePreferences(preferences: UserPreferences): Promise<UserPreferences> {
    const { data } = await api.post<UserPreferences>('/preferences/', preferences);
    return data;
  },

  async resetPreferences(userId: string = 'default') {
    const { data } = await api.delete(`/preferences/?user_id=${userId}`);
    return data;
  },

  async addRecentBuilding(buildingName: string, userId: string = 'default') {
    const { data } = await api.post(
      `/preferences/recent-building?building_name=${encodeURIComponent(buildingName)}&user_id=${userId}`
    );
    return data;
  },
};

export default apiService;
