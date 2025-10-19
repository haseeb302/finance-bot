import React from "react";
import ChatInterface from "../components/Chat/ChatInterface";

const ChatPage: React.FC = () => {
  return (
    <div className="flex flex-col w-full min-h-screen bg-background">
      <main className="flex flex-1 w-full">
        <ChatInterface />
      </main>
    </div>
  );
};

export default ChatPage;
