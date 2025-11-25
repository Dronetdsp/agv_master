/**
 * Main home page - Upload and start inference
 */
import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Upload as UploadIcon, Play, Loader2 } from 'lucide-react';
import { FileUpload } from '@/components/FileUpload';
import { ConfigPanel } from '@/components/ConfigPanel';
import { useAppStore } from '@/stores/useAppStore';
import { apiService } from '@/services/api';
import { useNavigate } from 'react-router-dom';

export const HomePage: React.FC = () => {
  const navigate = useNavigate();
  const { preferences, uploadedFiles, setUploadedFiles, clearUploadedFiles, setCurrentTaskId } =
    useAppStore();

  const [buildingName, setBuildingName] = useState('');
  const [config, setConfig] = useState(preferences.default_config);

  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (!buildingName || uploadedFiles.length === 0) {
        throw new Error('Please provide building name and upload images');
      }

      // Upload files
      await apiService.uploadImages(buildingName, uploadedFiles);

      // Start inference
      const response = await apiService.startInference({
        building_name: buildingName,
        config,
      });

      return response;
    },
    onSuccess: (response) => {
      setCurrentTaskId(response.task_id);
      clearUploadedFiles();
      navigate(`/results/${response.task_id}`);
    },
    onError: (error: any) => {
      alert(`Error: ${error.message || 'Upload failed'}`);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    uploadMutation.mutate();
  };

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="text-center mb-8">
        <h1 className="text-4xl font-bold mb-2">Crack Detection System</h1>
        <p className="text-gray-600">
          AI-powered facade defect detection and analysis
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Building Name */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <label className="block text-sm font-medium mb-2">
            Building / Project Name *
          </label>
          <input
            type="text"
            value={buildingName}
            onChange={(e) => setBuildingName(e.target.value)}
            placeholder="e.g., Building A, Bridge Inspection 2024"
            className="w-full px-4 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 outline-none"
            required
          />
        </div>

        {/* File Upload */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <UploadIcon className="w-5 h-5" />
            Upload Images
          </h3>
          <FileUpload
            files={uploadedFiles}
            onFilesChange={setUploadedFiles}
          />
        </div>

        {/* Configuration */}
        <ConfigPanel config={config} onChange={setConfig} />

        {/* Submit Button */}
        <div className="flex justify-end gap-4">
          <button
            type="button"
            onClick={() => {
              setBuildingName('');
              clearUploadedFiles();
              setConfig(preferences.default_config);
            }}
            className="px-6 py-3 border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
          >
            Reset
          </button>
          <button
            type="submit"
            disabled={
              !buildingName ||
              uploadedFiles.length === 0 ||
              uploadMutation.isPending
            }
            className="px-6 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {uploadMutation.isPending ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Processing...
              </>
            ) : (
              <>
                <Play className="w-5 h-5" />
                Start Analysis
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};
