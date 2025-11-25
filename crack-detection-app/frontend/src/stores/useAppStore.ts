/**
 * Global application state using Zustand
 * Lightweight state management with TypeScript
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { UserPreferences, InferenceConfig } from '@/types/api';

interface AppState {
  // User preferences
  preferences: UserPreferences;
  setPreferences: (preferences: Partial<UserPreferences>) => void;

  // Theme
  theme: 'light' | 'dark';
  toggleTheme: () => void;

  // Current building
  currentBuilding: string;
  setCurrentBuilding: (building: string) => void;

  // Upload state
  uploadedFiles: File[];
  setUploadedFiles: (files: File[]) => void;
  clearUploadedFiles: () => void;

  // Task tracking
  currentTaskId: string | null;
  setCurrentTaskId: (taskId: string | null) => void;
}

const defaultConfig: InferenceConfig = {
  imgsz: 1024,
  crack_conf: 0.25,
  det_conf: 0.35,
  mm_per_pixel: 1.0,
  min_box_px: 40,
  min_mask_area_px: 250,
  topk_base: 5,
  topk_max: 7,
  high_severity_th: 5000.0,
};

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      // Initial state
      preferences: {
        user_id: 'default',
        default_config: defaultConfig,
        theme: 'light',
        language: 'ko',
        recent_buildings: [],
      },

      theme: 'light',

      currentBuilding: '',

      uploadedFiles: [],

      currentTaskId: null,

      // Actions
      setPreferences: (preferences) =>
        set((state) => ({
          preferences: { ...state.preferences, ...preferences },
        })),

      toggleTheme: () =>
        set((state) => {
          const newTheme = state.theme === 'light' ? 'dark' : 'light';
          document.documentElement.classList.toggle('dark', newTheme === 'dark');
          return { theme: newTheme };
        }),

      setCurrentBuilding: (building) =>
        set({ currentBuilding: building }),

      setUploadedFiles: (files) =>
        set({ uploadedFiles: files }),

      clearUploadedFiles: () =>
        set({ uploadedFiles: [] }),

      setCurrentTaskId: (taskId) =>
        set({ currentTaskId: taskId }),
    }),
    {
      name: 'crack-detection-storage',
      partialize: (state) => ({
        preferences: state.preferences,
        theme: state.theme,
      }),
    }
  )
);
