import React from "react";
import { useChat } from "./ChatContext";
import { PlusCircle, Trash2 } from "lucide-react";
import { formatDate } from "../../lib/utils";

const ChatHistory: React.FC = () => {
  const { chats, currentChat, createNewChat, switchChat, deleteChat } =
    useChat();

  return (
    <div className="w-64 border-r bg-secondary/30 flex flex-col h-screen sticky top-0">
      {/* Sticky Header */}
      <div className="sticky top-0 z-10 bg-secondary/30 border-b p-4">
        <button
          onClick={createNewChat}
          className="w-full flex items-center justify-center gap-2 py-2 px-4 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
        >
          <PlusCircle size={16} />
          New Chat
        </button>
      </div>

      {/* Scrollable Chat List */}
      <div className="flex-1 overflow-y-auto min-h-0">
        {chats.length === 0 ? (
          <div className="p-4 text-sm text-muted-foreground">
            No chat history yet. Start a new chat!
          </div>
        ) : (
          <ul className="space-y-1 p-2">
            {chats.map((chat) => {
              return (
                <li
                  key={chat.id}
                  className={`rounded-md cursor-pointer transition-colors ${
                    currentChat?.id === chat.id
                      ? "bg-accent text-accent-foreground"
                      : "hover:bg-secondary"
                  }`}
                >
                  <div
                    className="p-3 flex flex-col"
                    onClick={() => switchChat(chat.id)}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <div className="font-medium truncate flex-1">
                        {chat.title || "New Chat"}
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteChat(chat.id);
                        }}
                        className="text-muted-foreground hover:text-destructive p-1 rounded-full"
                        aria-label="Delete chat"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>

                    <div className="text-xs text-muted-foreground">
                      {formatDate(chat.updated_at || chat.created_at)}
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
};
export default ChatHistory;
