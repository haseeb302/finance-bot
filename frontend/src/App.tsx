import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import Header from "./components/Layout/Header";
import { HomePage, ChatPage } from "./pages";
import ProtectedRoute from "./components/Layout/ProtectedRoute";
import GuestRoute from "./components/Layout/GuestRoute";
import { AuthProvider } from "./components/Auth/AuthContext";
import { ChatProvider } from "./components/Chat/ChatContext";
import ErrorBoundary from "./components/Layout/ErrorBoundary";

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
    mutations: {
      retry: 1,
    },
  },
});

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ErrorBoundary>
        <Router>
          <AuthProvider>
            <div className="flex flex-col w-full min-h-screen bg-background">
              <Header />
              <Routes>
                {/* Guest Routes */}
                <Route
                  path="/"
                  element={
                    <GuestRoute>
                      <ChatProvider>
                        <HomePage />
                      </ChatProvider>
                    </GuestRoute>
                  }
                />

                {/* Protected Routes */}
                <Route
                  path="/chat"
                  element={
                    <ProtectedRoute>
                      <ChatProvider>
                        <ChatPage />
                      </ChatProvider>
                    </ProtectedRoute>
                  }
                />
              </Routes>
              <Toaster
                position="top-right"
                toastOptions={{
                  duration: 4000,
                  style: {
                    background: "hsl(var(--card))",
                    color: "hsl(var(--card-foreground))",
                    border: "1px solid hsl(var(--border))",
                  },
                }}
              />
            </div>
          </AuthProvider>
        </Router>
      </ErrorBoundary>
    </QueryClientProvider>
  );
}
