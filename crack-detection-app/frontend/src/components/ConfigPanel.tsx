/**
 * Configuration panel for inference parameters
 * User-customizable settings
 */
import React from 'react';
import { Settings } from 'lucide-react';
import type { InferenceConfig } from '@/types/api';

interface ConfigPanelProps {
  config: InferenceConfig;
  onChange: (config: InferenceConfig) => void;
}

export const ConfigPanel: React.FC<ConfigPanelProps> = ({ config, onChange }) => {
  const updateConfig = (key: keyof InferenceConfig, value: number) => {
    onChange({ ...config, [key]: value });
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 space-y-4">
      <div className="flex items-center gap-2 mb-4">
        <Settings className="w-5 h-5" />
        <h3 className="text-lg font-semibold">Inference Configuration</h3>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Image Size */}
        <div>
          <label className="block text-sm font-medium mb-1">
            Image Size (px)
          </label>
          <input
            type="number"
            value={config.imgsz || 1024}
            onChange={(e) => updateConfig('imgsz', parseInt(e.target.value))}
            min={320}
            max={2048}
            step={32}
            className="w-full px-3 py-2 border rounded-md"
          />
        </div>

        {/* Crack Confidence */}
        <div>
          <label className="block text-sm font-medium mb-1">
            Crack Confidence (0-1)
          </label>
          <input
            type="number"
            value={config.crack_conf || 0.25}
            onChange={(e) => updateConfig('crack_conf', parseFloat(e.target.value))}
            min={0}
            max={1}
            step={0.05}
            className="w-full px-3 py-2 border rounded-md"
          />
        </div>

        {/* Detection Confidence */}
        <div>
          <label className="block text-sm font-medium mb-1">
            Detection Confidence (0-1)
          </label>
          <input
            type="number"
            value={config.det_conf || 0.35}
            onChange={(e) => updateConfig('det_conf', parseFloat(e.target.value))}
            min={0}
            max={1}
            step={0.05}
            className="w-full px-3 py-2 border rounded-md"
          />
        </div>

        {/* MM per Pixel */}
        <div>
          <label className="block text-sm font-medium mb-1">
            MM per Pixel (GSD)
          </label>
          <input
            type="number"
            value={config.mm_per_pixel || 1.0}
            onChange={(e) => updateConfig('mm_per_pixel', parseFloat(e.target.value))}
            min={0.1}
            max={10}
            step={0.1}
            className="w-full px-3 py-2 border rounded-md"
          />
        </div>

        {/* Min Box Size */}
        <div>
          <label className="block text-sm font-medium mb-1">
            Min Box Size (px)
          </label>
          <input
            type="number"
            value={config.min_box_px || 40}
            onChange={(e) => updateConfig('min_box_px', parseInt(e.target.value))}
            min={1}
            max={200}
            className="w-full px-3 py-2 border rounded-md"
          />
        </div>

        {/* Min Mask Area */}
        <div>
          <label className="block text-sm font-medium mb-1">
            Min Mask Area (px²)
          </label>
          <input
            type="number"
            value={config.min_mask_area_px || 250}
            onChange={(e) => updateConfig('min_mask_area_px', parseInt(e.target.value))}
            min={1}
            max={1000}
            className="w-full px-3 py-2 border rounded-md"
          />
        </div>

        {/* TopK Base */}
        <div>
          <label className="block text-sm font-medium mb-1">
            Top K (Base)
          </label>
          <input
            type="number"
            value={config.topk_base || 5}
            onChange={(e) => updateConfig('topk_base', parseInt(e.target.value))}
            min={1}
            max={20}
            className="w-full px-3 py-2 border rounded-md"
          />
        </div>

        {/* TopK Max */}
        <div>
          <label className="block text-sm font-medium mb-1">
            Top K (Max)
          </label>
          <input
            type="number"
            value={config.topk_max || 7}
            onChange={(e) => updateConfig('topk_max', parseInt(e.target.value))}
            min={1}
            max={30}
            className="w-full px-3 py-2 border rounded-md"
          />
        </div>
      </div>

      <div className="mt-4 p-3 bg-blue-50 rounded-md">
        <p className="text-sm text-blue-800">
          <strong>Tip:</strong> Lower confidence values detect more defects but may include false positives.
          Adjust mm_per_pixel based on your drone's GSD (Ground Sample Distance).
        </p>
      </div>
    </div>
  );
};
