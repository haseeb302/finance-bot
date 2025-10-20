import { api } from "../lib/api";
import { API_ENDPOINTS } from "../lib/config";
import {
  Chat,
  Message,
  ChatMessageRequest,
  ChatMessageResponse,
  PaginatedMessages,
  PaginatedChats,
} from "../types/chat";
import { ApiResponse, PaginationParams } from "../types/api";
import { WELCOME_MESSAGE } from "@/constants/welcomeMessage";

export class ChatService {
  /**
   * Get welcome message for new chat (constant, no API call)
   */
  static getWelcomeMessage(): Message {
    return {
      id: `welcome-${Date.now()}`,
      chat_id: "welcome",
      role: "assistant",
      content: WELCOME_MESSAGE,
      created_at: new Date().toISOString(),
      metadata: {},
    };
  }

  /**
   * Get user's chat sessions with pagination
   */
  static async getChats(
    params: PaginationParams = {}
  ): Promise<PaginatedChats> {
    try {
      const response = await api.get<PaginatedChats>(API_ENDPOINTS.CHAT.CHATS, {
        params,
      });

      // Ensure the response has the expected structure
      if (!response.data || typeof response.data !== "object") {
        console.error("Invalid response structure:", response.data);
        return {
          chats: [],
          total: 0,
          page: 1,
          page_size: 10,
          has_next: false,
          has_previous: false,
        };
      }

      // Ensure chats is an array
      if (!Array.isArray(response.data.chats)) {
        console.error("Chats is not an array:", response.data.chats);
        response.data.chats = [];
      }

      return response.data;
    } catch (error) {
      console.error("Error in getChats:", error);
      throw this.handleChatError(error);
    }
  }

  /**
   * Get specific chat by ID
   */
  static async getChat(chatId: string): Promise<Chat> {
    try {
      const response = await api.get<Chat>(
        API_ENDPOINTS.CHAT.CHAT_BY_ID(chatId)
      );
      return response.data;
    } catch (error) {
      throw this.handleChatError(error);
    }
  }

  /**
   * Update chat title
   */
  static async updateChat(chatId: string, title: string): Promise<Chat> {
    try {
      const response = await api.patch<Chat>(
        API_ENDPOINTS.CHAT.CHAT_BY_ID(chatId),
        { title }
      );
      return response.data;
    } catch (error) {
      throw this.handleChatError(error);
    }
  }

  /**
   * Delete chat
   */
  static async deleteChat(chatId: string): Promise<void> {
    try {
      await api.delete(API_ENDPOINTS.CHAT.CHAT_BY_ID(chatId));
    } catch (error) {
      throw this.handleChatError(error);
    }
  }

  /**
   * Get messages for a specific chat with pagination
   */
  static async getMessages(
    chatId: string,
    params: PaginationParams = {}
  ): Promise<PaginatedMessages> {
    try {
      const response = await api.get<PaginatedMessages>(
        API_ENDPOINTS.CHAT.MESSAGES(chatId),
        { params }
      );
      return response.data;
    } catch (error) {
      throw this.handleChatError(error);
    }
  }

  /**
   * Send message and get AI response
   */
  static async sendMessage(
    messageData: ChatMessageRequest
  ): Promise<ChatMessageResponse> {
    try {
      const response = await api.post<ChatMessageResponse>(
        API_ENDPOINTS.CHAT.MESSAGE,
        messageData,
        {
          timeout: 30000, // 30 seconds timeout for AI responses
        }
      );
      return response.data;
    } catch (error) {
      throw this.handleChatError(error);
    }
  }

  /**
   * Add message to existing chat
   */
  static async addMessageToChat(
    chatId: string,
    message: string
  ): Promise<ChatMessageResponse> {
    try {
      const response = await api.post<ChatMessageResponse>(
        API_ENDPOINTS.CHAT.MESSAGE,
        { message, chat_id: chatId }
      );
      return response.data;
    } catch (error) {
      throw this.handleChatError(error);
    }
  }

  /**
   * Search knowledge base (for admin functionality)
   */
  static async searchKnowledge(
    query: string,
    params: PaginationParams = {}
  ): Promise<{
    documents: Array<{
      id: number;
      title: string;
      content: string;
      category: string;
      source: string;
      similarity: number;
    }>;
    total: number;
  }> {
    try {
      const response = await api.get<
        ApiResponse<{
          documents: Array<{
            id: number;
            title: string;
            content: string;
            category: string;
            source: string;
            similarity: number;
          }>;
          total: number;
        }>
      >(API_ENDPOINTS.ADMIN.KNOWLEDGE_SEARCH, {
        params: { query, ...params },
      });
      return response.data.data;
    } catch (error) {
      throw this.handleChatError(error);
    }
  }

  /**
   * Handle chat errors consistently
   */
  private static handleChatError(error: unknown): Error {
    if (error && typeof error === "object" && "detail" in error) {
      return new Error((error as { detail: string }).detail);
    }

    if (error instanceof Error) {
      return error;
    }

    return new Error("An unexpected chat error occurred");
  }
}
