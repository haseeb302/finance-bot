import React, { useState } from "react";
import { useAuth } from "../../hooks/useAuth";
import AuthDialog from "../Auth/AuthDialog";

const Header = () => {
  const { user, logout, isLoading } = useAuth();
  const [showAuthDialog, setShowAuthDialog] = useState(false);
  return (
    <header className="w-full border-b border-border bg-background">
      <div className="container flex h-16 items-center justify-between">
        <div className="flex items-center">
          <h1 className="text-xl font-bold text-primary">FinanceBot</h1>
        </div>
        <div className="flex items-center gap-4">
          {user ? (
            <div className="flex items-center gap-4">
              <span className="text-sm text-muted-foreground">
                Hello, {user.username || user.full_name || user.email}
              </span>
              <button
                onClick={logout}
                disabled={isLoading}
                className="px-4 py-2 rounded-md bg-secondary text-secondary-foreground hover:bg-secondary/80 transition-colors disabled:opacity-50"
              >
                {isLoading ? "Logging out..." : "Logout"}
              </button>
            </div>
          ) : (
            <button
              onClick={() => setShowAuthDialog(true)}
              className="px-4 py-2 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              Login / Sign Up
            </button>
          )}
        </div>
      </div>
      <AuthDialog
        isOpen={showAuthDialog}
        onClose={() => setShowAuthDialog(false)}
      />
    </header>
  );
};
export default Header;
