import React, { createContext, useContext, useState, useEffect } from 'react';
import { AuthUser } from '../types';
import { apiClient } from '../api/client';

interface AuthContextType {
  currentUser: AuthUser | null;
  token: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const TOKEN_STORAGE_KEY = 'apex_care_auth_token';

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Validate active session on initial load
  useEffect(() => {
    const initializeAuth = async () => {
      const storedToken = localStorage.getItem(TOKEN_STORAGE_KEY);
      if (!storedToken) {
        setIsLoading(false);
        return;
      }

      try {
        const userProfile = await apiClient.getMe(storedToken);
        setCurrentUser({
          id: userProfile.id,
          email: userProfile.email,
          name: userProfile.name,
          role: userProfile.role,
          facility_id: userProfile.facility_id,
          patient_id: userProfile.patient_id,
        });
        setToken(storedToken);
      } catch (err) {
        console.warn('Session expired or invalid, clearing local credentials.');
        localStorage.removeItem(TOKEN_STORAGE_KEY);
        setCurrentUser(null);
        setToken(null);
      } finally {
        setIsLoading(false);
      }
    };

    initializeAuth();
  }, []);

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const response = await apiClient.login(email, password);
      const accessToken = response.access_token;
      const user = response.user;

      localStorage.setItem(TOKEN_STORAGE_KEY, accessToken);
      setToken(accessToken);
      setCurrentUser({
        id: user.id,
        email: user.email,
        name: user.name,
        role: user.role,
        facility_id: user.facility_id,
        patient_id: user.patient_id,
      });
    } catch (err: any) {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
      setToken(null);
      setCurrentUser(null);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    if (token) {
      await apiClient.logout(token);
    }
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    setToken(null);
    setCurrentUser(null);
  };

  return (
    <AuthContext.Provider value={{ currentUser, token, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
