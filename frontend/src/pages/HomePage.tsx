import React from "react";
import ChatInterface from "../components/Chat/ChatInterface";

const HomePage: React.FC = () => {
  return (
    <div className="flex flex-col w-full min-h-screen bg-background">
      <main className="flex flex-1 w-full px-10">
        <ChatInterface />
      </main>
    </div>
  );
};

export default HomePage;
