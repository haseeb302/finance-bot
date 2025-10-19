// Environment Configuration Types
interface Config {
  api: {
    baseURL: string;
    timeout: number;
  };
  app: {
    name: string;
    version: string;
  };
  features: {
    analytics: boolean;
    debug: boolean;
  };
}

// Environment Configuration
export const config: Config = {
  api: {
    baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000",
    timeout: Number(import.meta.env.VITE_API_TIMEOUT) || 30000, // Increased to 30 seconds for AI responses
  },
  app: {
    name: import.meta.env.VITE_APP_NAME || "FinanceBot",
    version: import.meta.env.VITE_APP_VERSION || "1.0.0",
  },
  features: {
    analytics: import.meta.env.VITE_ENABLE_ANALYTICS === "true",
    debug: import.meta.env.VITE_ENABLE_DEBUG === "true",
  },
} as const;

// API Endpoints Types
interface ApiEndpoints {
  AUTH: {
    LOGIN: string;
    REGISTER: string;
    SIGNIN: string;
    REFRESH: string;
    LOGOUT: string;
    ME: string;
    FORGOT_PASSWORD: string;
    RESET_PASSWORD: string;
    SESSIONS: string;
    SESSION_BY_ID: (sessionId: string) => string;
    DELETE_ALL_SESSIONS: string;
  };
  CHAT: {
    CHATS: string;
    MESSAGE: string;
    MESSAGES: (chatId: string) => string;
    CHAT_BY_ID: (chatId: string) => string;
  };
  ADMIN: {
    KNOWLEDGE: string;
    KNOWLEDGE_STATS: string;
    KNOWLEDGE_SEARCH: string;
    KNOWLEDGE_REINDEX: (docId: number) => string;
    KNOWLEDGE_REINDEX_ALL: string;
  };
}

// API Endpoints
export const API_ENDPOINTS: ApiEndpoints = {
  // Auth
  AUTH: {
    LOGIN: "/auth/login",
    REGISTER: "/auth/register",
    SIGNIN: "/auth/signin",
    REFRESH: "/auth/refresh",
    LOGOUT: "/auth/logout",
    ME: "/auth/me",
    FORGOT_PASSWORD: "/auth/forgot-password",
    RESET_PASSWORD: "/auth/reset-password",
    SESSIONS: "/auth/sessions",
    SESSION_BY_ID: (sessionId: string) => `/auth/sessions/${sessionId}`,
    DELETE_ALL_SESSIONS: "/auth/sessions/all",
  },
  // Chat
  CHAT: {
    CHATS: "/chat",
    MESSAGE: "/chat/message",
    MESSAGES: (chatId: string) => `/chat/${chatId}/messages`,
    CHAT_BY_ID: (chatId: string) => `/chat/${chatId}`,
  },
  // Admin
  ADMIN: {
    KNOWLEDGE: "/admin/knowledge",
    KNOWLEDGE_STATS: "/admin/knowledge/stats",
    KNOWLEDGE_SEARCH: "/admin/knowledge/search",
    KNOWLEDGE_REINDEX: (docId: number) => `/admin/knowledge/reindex/${docId}`,
    KNOWLEDGE_REINDEX_ALL: "/admin/knowledge/reindex-all",
  },
} as const;

// Storage Keys Types
interface StorageKeys {
  USER: string;
  TOKENS: string;
  CHAT_SESSIONS: (userId: number) => string;
  ANONYMOUS_SESSION: string;
}

// Storage Keys
export const STORAGE_KEYS: StorageKeys = {
  USER: "financebot-user",
  TOKENS: "financebot-tokens",
  CHAT_SESSIONS: (userId: number) => `chatSessions-${userId}`,
  ANONYMOUS_SESSION: "anonymous-chat-session",
} as const;

// Constants Types
interface Constants {
  MAX_MESSAGE_LENGTH: number;
  MAX_CHAT_TITLE_LENGTH: number;
  DEFAULT_PAGE_SIZE: number;
  MAX_PAGE_SIZE: number;
  TOKEN_REFRESH_THRESHOLD: number;
  DEBOUNCE_DELAY: number;
}

// Constants
export const CONSTANTS: Constants = {
  MAX_MESSAGE_LENGTH: 500,
  MAX_CHAT_TITLE_LENGTH: 255,
  DEFAULT_PAGE_SIZE: 3,
  MAX_PAGE_SIZE: 3,
  TOKEN_REFRESH_THRESHOLD: 5 * 60 * 1000, // 5 minutes
  DEBOUNCE_DELAY: 300,
} as const;
