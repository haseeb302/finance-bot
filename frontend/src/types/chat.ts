// Chat Types

export interface Message {
  id: string;
  chat_id: string;
  role: "user" | "assistant";
  content: string;
  metadata?: {
    tokens_used?: number;
    sources?: Source[];
    model?: string;
  };
  created_at: string;
}

export interface Chat {
  id: string;
  user_id?: string;
  title?: string;
  is_anonymous: boolean;
  created_at: string;
  updated_at?: string;
  message_count?: number;
}

export interface ChatMessageRequest {
  message: string;
  chat_id?: string;
  session_id?: string;
}

export interface ChatMessageResponse {
  message: Message;
  chat?: Chat;
  sources?: Source[];
  tokens_used?: number;
}

export interface Source {
  title: string;
  source: string;
  category: string;
  similarity: number;
}

export interface PaginatedMessages {
  messages: Message[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface PaginatedChats {
  chats: Chat[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface ChatSession {
  id: string;
  session_id: string;
  user_id?: string;
  is_anonymous: boolean;
  created_at: string;
  last_activity: string;
  is_active: boolean;
}

export interface ChatState {
  sessions: Chat[];
  currentSession: Chat | null;
  messages: Message[];
  isLoading: boolean;
  error: string | null;
}
