/**
 * Main App component with routing
 */
import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { HomePage } from '@/pages/HomePage';
import { ResultsPage } from '@/pages/ResultsPage';
import { Moon, Sun } from 'lucide-react';
import { useAppStore } from '@/stores/useAppStore';

// Create React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function App() {
  const { theme, toggleTheme } = useAppStore();

  React.useEffect(() => {
    // Apply theme on mount
    document.documentElement.classList.toggle('dark', theme === 'dark');
  }, [theme]);

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="min-h-screen bg-gray-50">
          {/* Header */}
          <header className="bg-white shadow-sm">
            <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
                  <span className="text-white font-bold text-xl">CD</span>
                </div>
                <div>
                  <h1 className="text-xl font-bold">Crack Detection</h1>
                  <p className="text-xs text-gray-500">AI-Powered Analysis</p>
                </div>
              </div>
              <button
                onClick={toggleTheme}
                className="p-2 hover:bg-gray-100 rounded-md transition-colors"
                title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
              >
                {theme === 'light' ? (
                  <Moon className="w-5 h-5" />
                ) : (
                  <Sun className="w-5 h-5" />
                )}
              </button>
            </div>
          </header>

          {/* Main Content */}
          <main className="py-8">
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/results/:taskId" element={<ResultsPage />} />
            </Routes>
          </main>

          {/* Footer */}
          <footer className="bg-white border-t mt-12">
            <div className="max-w-7xl mx-auto px-6 py-4 text-center text-sm text-gray-600">
              <p>© 2024 Crack Detection System | Powered by AI & Computer Vision</p>
            </div>
          </footer>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
