import {
  useEffect,
  useState,
  createContext,
  useContext,
  ReactNode,
  useCallback,
} from "react";
import { useAuth } from "../../hooks/useAuth";
import { Chat, Message, ChatMessageRequest } from "../../types/chat";
import { ChatService } from "../../services/chatService";
import { getErrorMessage } from "../../lib/utils";
import { CONSTANTS } from "../../lib/config";

interface ChatContextType {
  chats: Chat[];
  currentChat: Chat | null;
  messages: Message[];
  sendMessage: (text: string) => Promise<void>;
  clearChat: () => void;
  isLoading: boolean; // For message sending (thinking)
  isChatLoading: boolean; // For chat operations (switching, loading)
  error: string | null;
  createNewChat: () => Promise<void>;
  switchChat: (chatId: string) => Promise<void>;
  deleteChat: (chatId: string) => Promise<void>;
  loadMoreMessages: () => Promise<void>;
  hasMoreMessages: boolean;
  clearError: () => void;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

export const useChat = () => {
  const context = useContext(ChatContext);

  if (context === undefined) {
    throw new Error("useChat must be used within a ChatProvider");
  }
  return context;
};

export const ChatProvider = ({ children }: { children: ReactNode }) => {
  const [chats, setChats] = useState<Chat[]>([]);
  const [currentChat, setCurrentChat] = useState<Chat | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false); // For message sending
  const [isChatLoading, setIsChatLoading] = useState(false); // For chat operations
  const [error, setError] = useState<string | null>(null);
  const [hasMoreMessages, setHasMoreMessages] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);

  const { isAuthenticated } = useAuth();

  // Get welcome message (constant, no API call)
  const getWelcomeMessage = useCallback((): Message => {
    return ChatService.getWelcomeMessage();
  }, []);

  // Load user's chats
  const loadChats = useCallback(async () => {
    if (!isAuthenticated) return;

    try {
      setIsChatLoading(true);
      const response = await ChatService.getChats({
        page: 1,
        page_size: CONSTANTS.DEFAULT_PAGE_SIZE,
      });

      // Ensure response.chats exists and is an array
      const chats = response?.chats || [];
      setChats(chats);

      // Set the most recent chat as current if no current chat
      if (chats.length > 0) {
        setCurrentChat((prevCurrentChat) => {
          if (!prevCurrentChat) {
            return chats[0];
          }
          return prevCurrentChat;
        });
      }
    } catch (error) {
      const errorMessage = getErrorMessage(error);
      setError(errorMessage);
      console.error("Error loading chats:", error);
      // Set empty array as fallback
      setChats([]);
    } finally {
      setIsChatLoading(false);
    }
  }, [isAuthenticated]);

  // Load messages for current chat
  const loadMessages = useCallback(async (chatId: string, page = 1) => {
    try {
      setIsChatLoading(true);
      const response = await ChatService.getMessages(chatId, {
        page,
        page_size: CONSTANTS.DEFAULT_PAGE_SIZE,
      });

      if (page === 1) {
        setMessages(response.messages); // Backend already returns newest first
      } else {
        setMessages((prev) => {
          // Add older messages to the beginning (they're already in chronological order)
          const newMessages = [...response.messages, ...prev];
          return newMessages;
        });
      }

      setHasMoreMessages(response.has_next);
      setCurrentPage(page);
    } catch (error) {
      const errorMessage = getErrorMessage(error);
      setError(errorMessage);
      console.error("Error loading messages:", error);
    } finally {
      setIsChatLoading(false);
    }
  }, []);

  // Initialize chat for anonymous users
  const initializeAnonymousChat = useCallback(async () => {
    try {
      setIsChatLoading(true);

      // Create a temporary chat for anonymous users
      const tempChat: Chat = {
        id: "temp", // Temporary ID for anonymous chat
        user_id: undefined,
        title: "Start New Chat with FinanceBot",
        is_anonymous: true,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };

      setCurrentChat(tempChat);

      // Get welcome message (constant, no API call)
      const welcomeMessage = getWelcomeMessage();
      setMessages([welcomeMessage]);
    } catch (error) {
      const errorMessage = getErrorMessage(error);
      setError(errorMessage);
      console.error("Error initializing anonymous chat:", error);
    } finally {
      setIsChatLoading(false);
    }
  }, [getWelcomeMessage]);

  // Initialize on mount
  useEffect(() => {
    if (isAuthenticated) {
      loadChats();
    } else {
      initializeAnonymousChat();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated]); // Intentionally avoiding loadChats and initializeAnonymousChat to prevent circular dependencies

  // Load messages when currentChat changes (for authenticated users)
  useEffect(() => {
    if (isAuthenticated && currentChat && currentChat.id !== "temp") {
      loadMessages(currentChat.id, 1);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated, currentChat?.id]); // Intentionally avoiding loadMessages to prevent circular dependencies

  // Create new chat
  const createNewChat = useCallback(async () => {
    // For both authenticated and anonymous users, just show welcome message
    // No API call needed - chat will be created when user sends first message
    setCurrentChat(null);
    const welcomeMessage = getWelcomeMessage();
    setMessages([welcomeMessage]);
  }, [getWelcomeMessage]);

  // Switch to different chat
  const switchChat = useCallback(
    async (chatId: string) => {
      try {
        setIsChatLoading(true);
        setError(null);

        const chat = await ChatService.getChat(chatId);
        setCurrentChat(chat);
        setCurrentPage(1);
        await loadMessages(chatId, 1);
      } catch (error) {
        const errorMessage = getErrorMessage(error);
        setError(errorMessage);
        console.error("Error switching chat:", error);
      } finally {
        setIsChatLoading(false);
      }
    },
    [loadMessages]
  );

  // Delete chat
  const deleteChat = useCallback(
    async (chatId: string) => {
      try {
        setIsLoading(true);
        setError(null);

        await ChatService.deleteChat(chatId);

        // Update chats list
        setChats((prev) => {
          const updatedChats = (prev || []).filter(
            (chat) => chat.id !== chatId
          );

          // If deleting current chat, switch to another one or create new
          if (currentChat?.id === chatId) {
            if (updatedChats.length > 0) {
              const nextChat = updatedChats[0];
              setCurrentChat(nextChat);
              setCurrentPage(1);
              loadMessages(nextChat.id, 1);
            } else {
              // Create new chat for authenticated users
              if (isAuthenticated) {
                createNewChat();
              } else {
                // For anonymous users, just show welcome message
                setCurrentChat(null);
                const welcomeMessage = getWelcomeMessage();
                setMessages([welcomeMessage]);
              }
            }
          }

          return updatedChats;
        });
      } catch (error) {
        const errorMessage = getErrorMessage(error);
        setError(errorMessage);
        console.error("Error deleting chat:", error);
      } finally {
        setIsLoading(false);
      }
    },
    [
      currentChat?.id,
      isAuthenticated,
      loadMessages,
      createNewChat,
      getWelcomeMessage,
    ]
  );

  // Send message
  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || isLoading) return;

      const userMessage: Message = {
        id: `user-${Date.now()}`,
        chat_id: currentChat?.id || "temp",
        role: "user",
        content: text,
        created_at: new Date().toISOString(),
      };

      // Add user message immediately
      setMessages((prev) => [...prev, userMessage]);
      setIsLoading(true);
      setError(null);

      try {
        const messageData: ChatMessageRequest = {
          message: text,
          chat_id: currentChat?.id === "temp" ? undefined : currentChat?.id,
        };

        // Retry logic for network errors
        let response;
        let retryCount = 0;
        const maxRetries = 2;

        while (retryCount <= maxRetries) {
          try {
            response = await ChatService.sendMessage(messageData);
            break; // Success, exit retry loop
          } catch (error: unknown) {
            if (
              error &&
              typeof error === "object" &&
              "status_code" in error &&
              "type" in error
            ) {
              const apiError = error as { status_code: number; type: string };
              if (
                apiError.status_code === 0 ||
                apiError.type === "network_error"
              ) {
                // Network error, retry
                retryCount++;
                if (retryCount <= maxRetries) {
                  await new Promise((resolve) =>
                    setTimeout(resolve, 1000 * retryCount)
                  ); // Exponential backoff
                  continue;
                }
              }
            }
            throw error; // Re-throw if not network error or max retries reached
          }
        }

        // Validate response structure
        if (!response || !response.message) {
          throw new Error("Invalid response from server");
        }

        // Add bot response
        setMessages((prev) => [...prev, response.message]);

        // Update current chat if it's a new chat
        if (response.chat && response.chat.id !== currentChat?.id) {
          const chat = response.chat;
          setCurrentChat(chat);
          setChats((prev) => [chat, ...prev]);
        }
      } catch (error) {
        const errorMessage = getErrorMessage(error);
        setError(errorMessage);

        // Add error message
        const errorMsg: Message = {
          id: `error-${Date.now()}`,
          chat_id: currentChat?.id || "temp",
          role: "assistant",
          content:
            "I'm sorry, I'm having trouble processing your request right now. Please try again later.",
          created_at: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, errorMsg]);
      } finally {
        setIsLoading(false);
      }
    },
    [currentChat?.id, isLoading]
  );

  // Load more messages (pagination)
  const loadMoreMessages = useCallback(async () => {
    if (!currentChat || !hasMoreMessages || isChatLoading) return;

    try {
      await loadMessages(currentChat.id, currentPage + 1);
    } catch (error) {
      const errorMessage = getErrorMessage(error);
      setError(errorMessage);
      console.error("Error loading more messages:", error);
    }
  }, [currentChat, hasMoreMessages, isChatLoading, currentPage, loadMessages]);

  // Clear current chat
  const clearChat = useCallback(() => {
    const welcomeMessage = getWelcomeMessage();
    setMessages([welcomeMessage]);
  }, [getWelcomeMessage]);

  // Clear error
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const value: ChatContextType = {
    chats,
    currentChat,
    messages,
    sendMessage,
    clearChat,
    isLoading,
    isChatLoading,
    error,
    createNewChat,
    switchChat,
    deleteChat,
    loadMoreMessages,
    hasMoreMessages,
    clearError,
  };

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>;
};
