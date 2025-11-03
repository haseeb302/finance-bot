import React from "react";
import MessageList from "./MessageList";
import MessageInput from "./MessageInput";
import ChatHistory from "./ChatHistory";
import { useChat } from "./ChatContext";
import { useAuth } from "../../hooks/useAuth";
import { PlusCircle } from "lucide-react";
import toast from "react-hot-toast";

const ChatInterface = () => {
  const {
    currentChat,
    messages,
    sendMessage,
    isLoading,
    isChatLoading,
    error,
    createNewChat,
    loadMoreMessages,
    hasMoreMessages,
    clearError,
  } = useChat();
  const { isAuthenticated } = useAuth();

  // Handle error display
  React.useEffect(() => {
    if (error) {
      toast.error(error);
      clearError();
    }
  }, [error, clearError]);

  return (
    <div className="flex w-full h-screen">
      {/* Chat History Sidebar - Only visible for authenticated users */}
      {isAuthenticated && <ChatHistory />}

      {/* Main Chat Area - Sticky and full height */}
      <div className="flex flex-col flex-1 h-screen">
        {/* Chat Header - Sticky at top */}
        <div className="sticky top-0 z-10 bg-background border-b p-4">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-medium">
              {currentChat?.title || "Chat with FinanceBot"}
            </h2>
            <div className="flex items-center gap-2">
              {/* Only show New Chat button for authenticated users */}
              {isAuthenticated && (
                <button
                  onClick={createNewChat}
                  className="flex items-center text-sm text-muted-foreground hover:text-primary"
                  disabled={isLoading}
                >
                  <PlusCircle size={16} className="mr-1" />
                  New Chat
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Chat Messages Area - Scrollable */}
        <div className="flex-1 flex flex-col min-h-0">
          <div className="flex-1 overflow-hidden">
            <MessageList
              messages={messages}
              isLoading={isLoading}
              isChatLoading={isChatLoading}
              hasMoreMessages={hasMoreMessages}
              onLoadMore={loadMoreMessages}
            />
          </div>

          {/* Message Input - Sticky at bottom */}
          <div className="sticky bottom-0 bg-background border-t p-4">
            <MessageInput onSendMessage={sendMessage} isLoading={isLoading} />
          </div>
        </div>

        {/* Footer Info */}
        <div className="p-4 text-xs text-center text-muted-foreground border-t bg-muted/30">
          <p>
            FinanceBot can answer questions about account registration,
            payments, security, regulations, and technical support.
          </p>
          {!isAuthenticated && (
            <p className="mt-1">
              Sign in to save your chat history and access it later.
            </p>
          )}
        </div>
      </div>
    </div>
  );
};
export default ChatInterface;
