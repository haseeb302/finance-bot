import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from "axios";
import { config, STORAGE_KEYS } from "./config";
import { ApiError, RequestConfig } from "../types/api";
import { TokenResponse } from "../types/auth";

// Create axios instance
const apiClient: AxiosInstance = axios.create({
  baseURL: config.api.baseURL,
  timeout: config.api.timeout,
  headers: {
    "Content-Type": "application/json",
    "ngrok-skip-browser-warning": "true", // Skip ngrok browser warning
  },
});

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  (config) => {
    const tokens = getStoredTokens();

    // Check if this is an auth endpoint that doesn't require authentication
    const isAuthEndpoint =
      config.url?.includes("/auth/") &&
      (config.url?.includes("/login") ||
        config.url?.includes("/register") ||
        config.url?.includes("/signin") ||
        config.url?.includes("/forgot-password") ||
        config.url?.includes("/reset-password"));

    if (tokens?.access_token) {
      config.headers.Authorization = `Bearer ${tokens.access_token}`;
    } else if (!isAuthEndpoint) {
      // Only redirect if it's not an auth endpoint and no tokens exist
      clearStoredTokens();
      window.location.href = "/";
    }

    // Ensure ngrok-skip-browser-warning header is always present
    config.headers["ngrok-skip-browser-warning"] = "true";

    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling and token refresh
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    return response;
  },
  async (error) => {
    const originalRequest = error.config;

    // Check if this is an auth endpoint
    const isAuthEndpoint =
      originalRequest?.url?.includes("/auth/") &&
      (originalRequest?.url?.includes("/login") ||
        originalRequest?.url?.includes("/register") ||
        originalRequest?.url?.includes("/signin") ||
        originalRequest?.url?.includes("/forgot-password") ||
        originalRequest?.url?.includes("/reset-password"));

    // Handle 401 errors (token expired) - but not for auth endpoints
    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !isAuthEndpoint
    ) {
      originalRequest._retry = true;

      try {
        const tokens = getStoredTokens();
        if (tokens?.refresh_token) {
          const newTokens = await refreshTokens(tokens.refresh_token);
          storeTokens(newTokens);

          // Retry original request with new token
          originalRequest.headers.Authorization = `Bearer ${newTokens.access_token}`;
          return apiClient(originalRequest);
        }
      } catch (refreshError) {
        // Refresh failed, redirect to home only if not an auth endpoint
        if (!isAuthEndpoint) {
          clearStoredTokens();
          window.location.href = "/";
        }
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(transformError(error));
  }
);

// Token management functions
export const getStoredTokens = (): TokenResponse | null => {
  try {
    const tokens = localStorage.getItem(STORAGE_KEYS.TOKENS);
    return tokens ? JSON.parse(tokens) : null;
  } catch {
    return null;
  }
};

export const storeTokens = (tokens: TokenResponse): void => {
  localStorage.setItem(STORAGE_KEYS.TOKENS, JSON.stringify(tokens));
};

export const clearStoredTokens = () => {
  localStorage.removeItem(STORAGE_KEYS.TOKENS);
};

// Token refresh function
const refreshTokens = async (refreshToken: string): Promise<TokenResponse> => {
  const response = await axios.post<TokenResponse>(
    `${config.api.baseURL}/auth/refresh`,
    {
      refresh_token: refreshToken,
    }
  );
  return response.data;
};

// Error transformation
const transformError = (error: unknown): ApiError => {
  if (error && typeof error === "object" && "response" in error) {
    const axiosError = error as {
      response: {
        data?: {
          detail?: string;
          type?: string;
        };
        status: number;
      };
    };
    return {
      detail: axiosError.response.data?.detail || "An error occurred",
      status_code: axiosError.response.status,
      type: axiosError.response.data?.type,
    };
  } else if (error && typeof error === "object" && "request" in error) {
    return {
      detail: "Network error - please check your connection",
      status_code: 0,
      type: "network_error",
    };
  } else if (error instanceof Error) {
    return {
      detail: error.message || "An unexpected error occurred",
      status_code: 500,
      type: "unknown_error",
    };
  } else {
    return {
      detail: "An unexpected error occurred",
      status_code: 500,
      type: "unknown_error",
    };
  }
};

// Generic API request function
export const apiRequest = async <T = unknown>(
  requestConfig: RequestConfig
): Promise<T> => {
  const response: AxiosResponse<T> = await apiClient.request({
    url: requestConfig.url,
    method: requestConfig.method,
    data: requestConfig.data,
    params: requestConfig.params,
    headers: requestConfig.headers,
    timeout: requestConfig.timeout,
  });
  return response.data;
};

// HTTP method helpers
export const api = {
  get: <T = unknown>(url: string, config?: AxiosRequestConfig) =>
    apiClient.get<T>(url, config),
  post: <T = unknown>(
    url: string,
    data?: unknown,
    config?: AxiosRequestConfig
  ) => apiClient.post<T>(url, data, config),
  put: <T = unknown>(
    url: string,
    data?: unknown,
    config?: AxiosRequestConfig
  ) => apiClient.put<T>(url, data, config),
  patch: <T = unknown>(
    url: string,
    data?: unknown,
    config?: AxiosRequestConfig
  ) => apiClient.patch<T>(url, data, config),
  delete: <T = unknown>(url: string, config?: AxiosRequestConfig) =>
    apiClient.delete<T>(url, config),
};

export default apiClient;
