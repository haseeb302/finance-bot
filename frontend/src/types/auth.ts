// Authentication Types
export interface User {
  id: string; // Changed from number to string for UUID
  email: string;
  username: string;
  full_name?: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  updated_at?: string;
  last_login?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  username: string;
  full_name?: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface RefreshTokenRequest {
  refresh_token: string;
}

export interface AuthError {
  detail: string;
  status_code?: number;
}

export interface Session {
  session_id: string;
  user_id: string;
  access_token: string;
  refresh_token: string;
  is_active: boolean;
  created_at: string;
  expires_at: string;
  last_activity?: string;
  device_info?: string;
  ip_address?: string;
}

export interface SessionListResponse {
  sessions: Session[];
  total: number;
}

export interface AuthState {
  user: User | null;
  tokens: TokenResponse | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}
