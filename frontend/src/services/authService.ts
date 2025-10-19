import { api } from "../lib/api";
import { API_ENDPOINTS } from "../lib/config";
import {
  User,
  LoginRequest,
  RegisterRequest,
  TokenResponse,
  AuthError,
} from "../types/auth";
import { ApiResponse } from "../types/api";

export class AuthService {
  /**
   * Login user with email and password
   */
  static async login(credentials: LoginRequest): Promise<TokenResponse> {
    try {
      const response = await api.post<ApiResponse<TokenResponse>>(
        API_ENDPOINTS.AUTH.LOGIN,
        credentials
      );
      return response.data.data;
    } catch (error) {
      throw this.handleAuthError(error);
    }
  }

  /**
   * Register new user
   */
  static async register(userData: RegisterRequest): Promise<TokenResponse> {
    try {
      const response = await api.post<ApiResponse<TokenResponse>>(
        API_ENDPOINTS.AUTH.REGISTER,
        userData
      );
      return response.data.data;
    } catch (error) {
      throw this.handleAuthError(error);
    }
  }

  /**
   * Unified signin - creates account if user doesn't exist, otherwise logs in
   */
  static async signin(credentials: LoginRequest): Promise<TokenResponse> {
    try {
      const response = await api.post<TokenResponse>(
        API_ENDPOINTS.AUTH.SIGNIN,
        credentials
      );
      return response.data;
    } catch (error) {
      throw this.handleAuthError(error);
    }
  }

  /**
   * Refresh access token using refresh token
   */
  static async refreshToken(refreshToken: string): Promise<TokenResponse> {
    try {
      const response = await api.post<ApiResponse<TokenResponse>>(
        API_ENDPOINTS.AUTH.REFRESH,
        { refresh_token: refreshToken }
      );
      return response.data.data;
    } catch (error) {
      throw this.handleAuthError(error);
    }
  }

  /**
   * Get current user profile
   */
  static async getCurrentUser(): Promise<User> {
    try {
      const response = await api.get<User>(API_ENDPOINTS.AUTH.ME);
      return response.data;
    } catch (error) {
      throw this.handleAuthError(error);
    }
  }

  /**
   * Logout user (revoke refresh token)
   */
  static async logout(): Promise<void> {
    try {
      await api.post(API_ENDPOINTS.AUTH.LOGOUT);
    } catch (error) {
      // Don't throw error for logout, just log it
      console.warn("Logout error:", error);
    }
  }

  /**
   * Request password reset
   */
  static async forgotPassword(email: string): Promise<void> {
    try {
      await api.post(API_ENDPOINTS.AUTH.FORGOT_PASSWORD, { email });
    } catch (error) {
      throw this.handleAuthError(error);
    }
  }

  /**
   * Reset password with token
   */
  static async resetPassword(
    token: string,
    newPassword: string
  ): Promise<void> {
    try {
      await api.post(API_ENDPOINTS.AUTH.RESET_PASSWORD, {
        token,
        new_password: newPassword,
      });
    } catch (error) {
      throw this.handleAuthError(error);
    }
  }

  /**
   * Handle authentication errors consistently
   */
  private static handleAuthError(error: unknown): AuthError {
    if (error && typeof error === "object" && "detail" in error) {
      return {
        detail: (error as { detail: string }).detail,
        status_code: (error as { status_code?: number }).status_code || 500,
      };
    }

    if (error instanceof Error) {
      return {
        detail: error.message,
        status_code: 500,
      };
    }

    return {
      detail: "An unexpected authentication error occurred",
      status_code: 500,
    };
  }
}
