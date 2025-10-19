import {
  useEffect,
  useState,
  createContext,
  useContext,
  ReactNode,
  useCallback,
} from "react";
import { useNavigate } from "react-router-dom";
import { User, LoginRequest, RegisterRequest } from "../../types/auth";
import { AuthService } from "../../services/authService";
import { storage, getErrorMessage } from "../../lib/utils";
import { STORAGE_KEYS } from "../../lib/config";
interface AuthContextType {
  user: User | null;
  login: (credentials: LoginRequest) => Promise<void>;
  register: (userData: RegisterRequest) => Promise<void>;
  signin: (credentials: LoginRequest) => Promise<void>;
  logout: () => Promise<void>;
  isAuthenticated: boolean;
  isLoading: boolean;
  isInitializing: boolean; // New: for initial auth check
  error: string | null;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isInitializing, setIsInitializing] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  // Check for saved user and tokens on mount
  useEffect(() => {
    const initializeAuth = async () => {
      try {
        setIsInitializing(true);
        const savedUser = storage.get<User>(STORAGE_KEYS.USER);
        const savedTokens = storage.get(STORAGE_KEYS.TOKENS);

        if (savedUser && savedTokens) {
          // Verify token is still valid by fetching current user
          try {
            const currentUser = await AuthService.getCurrentUser();
            setUser(currentUser);
          } catch (error) {
            // Token is invalid, clear stored data
            storage.remove(STORAGE_KEYS.USER);
            storage.remove(STORAGE_KEYS.TOKENS);
            setUser(null);
          }
        }
      } catch (error) {
        console.error("Error initializing auth:", error);
        // Clear any corrupted data
        storage.remove(STORAGE_KEYS.USER);
        storage.remove(STORAGE_KEYS.TOKENS);
      } finally {
        setIsInitializing(false);
      }
    };

    initializeAuth();
  }, []);

  // Login function
  const login = useCallback(async (credentials: LoginRequest) => {
    setIsLoading(true);
    setError(null);

    try {
      const tokens = await AuthService.login(credentials);
      const currentUser = await AuthService.getCurrentUser();

      // Store tokens and user data
      storage.set(STORAGE_KEYS.TOKENS, tokens);
      storage.set(STORAGE_KEYS.USER, currentUser);

      setUser(currentUser);
    } catch (error) {
      const errorMessage = getErrorMessage(error);
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Register function
  const register = useCallback(async (userData: RegisterRequest) => {
    setIsLoading(true);
    setError(null);

    try {
      const tokens = await AuthService.register(userData);
      const currentUser = await AuthService.getCurrentUser();

      // Store tokens and user data
      storage.set(STORAGE_KEYS.TOKENS, tokens);
      storage.set(STORAGE_KEYS.USER, currentUser);

      setUser(currentUser);
    } catch (error) {
      const errorMessage = getErrorMessage(error);
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Unified signin function - creates account if user doesn't exist, otherwise logs in
  const signin = useCallback(
    async (credentials: LoginRequest) => {
      setIsLoading(true);
      setError(null);

      try {
        const tokens = await AuthService.signin(credentials);
        console.log("Signin successful, tokens received:", tokens);

        // Store tokens first
        storage.set(STORAGE_KEYS.TOKENS, tokens);
        console.log("Tokens stored in localStorage");

        // Then try to get current user
        const currentUser = await AuthService.getCurrentUser();
        console.log("Current user fetched:", currentUser);

        // Store user data
        storage.set(STORAGE_KEYS.USER, currentUser);
        console.log("User data stored in localStorage");

        setUser(currentUser);
        console.log("User state updated:", currentUser);

        // Navigate to chat page after successful login
        navigate("/chat");
      } catch (error) {
        const errorMessage = getErrorMessage(error);
        setError(errorMessage);
        throw new Error(errorMessage);
      } finally {
        setIsLoading(false);
      }
    },
    [navigate]
  );

  // Logout function
  const logout = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      await AuthService.logout();
    } catch (error) {
      console.warn("Logout error:", error);
    } finally {
      // Clear local state regardless of API call success
      storage.remove(STORAGE_KEYS.USER);
      storage.remove(STORAGE_KEYS.TOKENS);
      setUser(null);
      setIsLoading(false);

      // Navigate to home page after logout
      navigate("/");
    }
  }, [navigate]);

  // Clear error function
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const value: AuthContextType = {
    user,
    login,
    register,
    signin,
    logout,
    isAuthenticated: !!user,
    isLoading,
    isInitializing,
    error,
    clearError,
  };

  // Debug logging for user state changes
  useEffect(() => {
    console.log("AuthContext - User state changed:", user);
    console.log("AuthContext - Is authenticated:", !!user);
  }, [user]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
