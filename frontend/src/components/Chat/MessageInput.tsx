import React, { useState, useRef, useEffect } from "react";
import { Send, Loader2 } from "lucide-react";
import { CONSTANTS } from "../../lib/config";

interface MessageInputProps {
  onSendMessage: (text: string) => Promise<void>;
  isLoading: boolean;
}

const MessageInput: React.FC<MessageInputProps> = ({
  onSendMessage,
  isLoading,
}) => {
  const [message, setMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [message]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && !isLoading && !isSubmitting) {
      const messageToSend = message.trim();
      setMessage(""); // Clear input immediately
      setIsSubmitting(true);
      try {
        await onSendMessage(messageToSend);
      } catch (error) {
        console.error("Error sending message:", error);
        // Restore message if sending failed
        setMessage(messageToSend);
      } finally {
        setIsSubmitting(false);
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const isDisabled = !message.trim() || isLoading || isSubmitting;

  return (
    <form onSubmit={handleSubmit} className="flex gap-3">
      <div className="flex-1 relative">
        <textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type your question here... (Press Enter to send, Shift+Enter for new line)"
          className="w-full px-4 py-3 pr-16 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary bg-background resize-none min-h-[44px] max-h-[120px]"
          disabled={isLoading || isSubmitting}
          maxLength={CONSTANTS.MAX_MESSAGE_LENGTH}
          rows={1}
        />
        <div className="absolute bottom-3 right-3 text-xs text-muted-foreground bg-background px-1 rounded">
          {message.length}/{CONSTANTS.MAX_MESSAGE_LENGTH}
        </div>
      </div>
      <button
        type="submit"
        disabled={isDisabled}
        className="h-11 w-11 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center flex-shrink-0"
        title={isDisabled ? "Please enter a message" : "Send message"}
      >
        {isSubmitting ? (
          <Loader2 size={18} className="animate-spin" />
        ) : (
          <Send size={18} />
        )}
      </button>
    </form>
  );
};
export default MessageInput;
