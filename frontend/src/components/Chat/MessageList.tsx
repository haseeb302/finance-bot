import React, { useEffect, useRef } from "react";
import { Loader2, ChevronUp } from "lucide-react";
import { Message } from "../../types/chat";
import { formatTime } from "../../lib/utils";
import MarkdownMessage from "./MarkdownMessage";

interface MessageListProps {
  messages: Message[];
  isLoading: boolean; // For message sending (thinking)
  isChatLoading?: boolean; // For chat operations (switching, loading)
  hasMoreMessages?: boolean;
  onLoadMore?: () => void;
}

const MessageList: React.FC<MessageListProps> = ({
  messages,
  isLoading,
  isChatLoading = false,
  hasMoreMessages = false,
  onLoadMore,
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [messages]);
  return (
    <div className="h-full overflow-y-auto p-4 space-y-4">
      {/* Load More Button */}
      {hasMoreMessages && onLoadMore && (
        <div className="flex justify-center py-2">
          <button
            onClick={onLoadMore}
            disabled={isLoading}
            className="flex items-center gap-2 px-4 py-2 text-sm text-muted-foreground hover:text-foreground border border-border rounded-md hover:bg-secondary transition-colors disabled:opacity-50"
          >
            <ChevronUp size={16} />
            Load More Messages
          </button>
        </div>
      )}

      {messages.map((message) => (
        <div
          key={message.id}
          className={`flex ${
            message.role === "user" ? "justify-end" : "justify-start"
          }`}
        >
          <div
            className={`max-w-[80%] rounded-lg px-4 py-2 ${
              message.role === "user"
                ? "bg-primary text-primary-foreground"
                : "bg-secondary text-secondary-foreground"
            }`}
          >
            {message.role === "assistant" ? (
              <MarkdownMessage content={message.content} className="text-sm" />
            ) : (
              <div className="text-sm whitespace-pre-wrap">
                {message.content}
              </div>
            )}
            <div className="text-xs mt-1 opacity-70">
              {formatTime(message.created_at)}
            </div>
          </div>
        </div>
      ))}

      {isLoading && (
        <div className="flex justify-start">
          <div className="bg-secondary text-secondary-foreground rounded-lg px-4 py-2 flex items-center">
            <Loader2 size={16} className="animate-spin mr-2" />
            <span className="text-sm">Thinking...</span>
          </div>
        </div>
      )}

      {isChatLoading && (
        <div className="flex justify-center py-4">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Loader2 size={16} className="animate-spin" />
            <span className="text-sm">Loading chat...</span>
          </div>
        </div>
      )}

      <div ref={messagesEndRef} />
    </div>
  );
};
export default MessageList;
