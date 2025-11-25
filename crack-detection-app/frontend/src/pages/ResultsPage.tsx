/**
 * Results page - Real-time progress and final results
 */
import React, { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Download, Home, BarChart } from 'lucide-react';
import { ProgressBar } from '@/components/ProgressBar';
import { apiService } from '@/services/api';
import { getDefectColor, formatNumber, getSeverityLevel } from '@/lib/utils';

export const ResultsPage: React.FC = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();

  // Poll task status
  const { data, isLoading } = useQuery({
    queryKey: ['taskStatus', taskId],
    queryFn: () => apiService.getTaskStatus(taskId!),
    enabled: !!taskId,
    refetchInterval: (data) => {
      // Stop polling when completed or failed
      if (data?.status === 'completed' || data?.status === 'failed') {
        return false;
      }
      return 2000; // Poll every 2 seconds
    },
  });

  if (isLoading || !data) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4" />
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Analysis Results</h1>
          <p className="text-gray-600">{data.building_name}</p>
        </div>
        <button
          onClick={() => navigate('/')}
          className="flex items-center gap-2 px-4 py-2 border rounded-md hover:bg-gray-50"
        >
          <Home className="w-4 h-4" />
          New Analysis
        </button>
      </div>

      {/* Progress */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold mb-4">Progress</h2>
        <ProgressBar
          progress={data.progress}
          status={data.status}
          message={data.message}
        />
      </div>

      {/* Statistics */}
      {data.stats && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <BarChart className="w-5 h-5" />
            Statistics
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="p-4 bg-blue-50 rounded-lg">
              <p className="text-sm text-gray-600">Total Images</p>
              <p className="text-2xl font-bold text-blue-600">
                {data.stats.num_images}
              </p>
            </div>
            <div className="p-4 bg-red-50 rounded-lg">
              <p className="text-sm text-gray-600">Total Defects</p>
              <p className="text-2xl font-bold text-red-600">
                {data.stats.total_defects}
              </p>
            </div>
            <div className="p-4 bg-amber-50 rounded-lg">
              <p className="text-sm text-gray-600">Mean Severity</p>
              <p className="text-2xl font-bold text-amber-600">
                {formatNumber(data.stats.mean_severity)}
              </p>
            </div>
          </div>

          {/* By Class */}
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-100">
                <tr>
                  <th className="px-4 py-2 text-left">Defect Type</th>
                  <th className="px-4 py-2 text-right">Count</th>
                  <th className="px-4 py-2 text-right">Mean Severity</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(data.stats.by_class).map(([className, info]) => (
                  <tr key={className} className="border-t">
                    <td className="px-4 py-2">
                      <div className="flex items-center gap-2">
                        <div
                          className="w-3 h-3 rounded-full"
                          style={{ backgroundColor: getDefectColor(className) }}
                        />
                        <span className="font-medium capitalize">{className}</span>
                      </div>
                    </td>
                    <td className="px-4 py-2 text-right">{info.count}</td>
                    <td className="px-4 py-2 text-right">
                      <span
                        className="px-2 py-1 rounded text-sm font-medium"
                        style={{
                          backgroundColor: `${getSeverityLevel(info.mean_severity).color}20`,
                          color: getSeverityLevel(info.mean_severity).color,
                        }}
                      >
                        {formatNumber(info.mean_severity)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Severe Findings */}
      {data.severe_findings && data.severe_findings.length > 0 && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold mb-4">Top Severe Defects</h2>
          <div className="space-y-4">
            {data.severe_findings.map((finding, index) => (
              <div
                key={index}
                className="border rounded-lg p-4 hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <span className="text-xl font-bold text-gray-400">
                        #{index + 1}
                      </span>
                      <h3 className="font-semibold text-lg capitalize">
                        {finding.type}
                      </h3>
                      <span
                        className="px-3 py-1 rounded-full text-sm font-medium"
                        style={{
                          backgroundColor: `${getSeverityLevel(finding.severity).color}20`,
                          color: getSeverityLevel(finding.severity).color,
                        }}
                      >
                        {getSeverityLevel(finding.severity).label}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 mb-2">{finding.image}</p>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm">
                      <div>
                        <span className="text-gray-500">Severity: </span>
                        <span className="font-medium">
                          {formatNumber(finding.severity)}
                        </span>
                      </div>
                      {finding.length_mm && (
                        <div>
                          <span className="text-gray-500">Length: </span>
                          <span className="font-medium">
                            {formatNumber(finding.length_mm)} mm
                          </span>
                        </div>
                      )}
                      {finding.width_mm && (
                        <div>
                          <span className="text-gray-500">Width: </span>
                          <span className="font-medium">
                            {formatNumber(finding.width_mm)} mm
                          </span>
                        </div>
                      )}
                      {finding.area_mm2 && (
                        <div>
                          <span className="text-gray-500">Area: </span>
                          <span className="font-medium">
                            {formatNumber(finding.area_mm2)} mm²
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Download Reports */}
      {data.status === 'completed' && data.report_pdf_url && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <Download className="w-5 h-5" />
            Download Reports
          </h2>
          <div className="flex gap-4">
            <a
              href={data.report_pdf_url}
              download
              className="px-6 py-3 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
            >
              Download PDF Report
            </a>
            {data.report_html_url && (
              <a
                href={data.report_html_url}
                download
                className="px-6 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
              >
                Download HTML Report
              </a>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
