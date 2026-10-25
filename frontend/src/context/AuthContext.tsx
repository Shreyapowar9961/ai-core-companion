import React, { createContext, useContext, useState, useEffect } from 'react';
import { AuthUser, UserRole } from '../types';

interface AuthContextType {
  currentUser: AuthUser;
  switchRole: (role: UserRole) => void;
  token: string;
}

const DEMO_USERS: Record<UserRole, AuthUser> = {
  CLINICIAN: {
    id: 'doc-101',
    name: 'Dr. Neha Kulkarni',
    email: 'dr.neha@apexcare.org',
    role: 'CLINICIAN',
    facility_id: 'facility-apex-1'
  },
  ADMIN: {
    id: 'admin-1',
    name: 'Rajesh Sharma (Admin)',
    email: 'admin@apexcare.org',
    role: 'ADMIN',
    facility_id: 'facility-apex-1'
  },
  CAREGIVER: {
    id: 'cg-101',
    name: 'Suresh Patil (Son & Caregiver)',
    email: 'suresh.patil@example.com',
    role: 'CAREGIVER',
    patient_id: 'patient-demo-1'
  },
  PATIENT: {
    id: 'patient-demo-1',
    name: 'Ramesh Patil (Patient)',
    email: 'ramesh.patil@example.com',
    role: 'PATIENT',
    patient_id: 'patient-demo-1'
  }
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentUser, setCurrentUser] = useState<AuthUser>(DEMO_USERS.CLINICIAN);
  const [token, setToken] = useState<string>('');

  const generateDemoToken = (user: AuthUser): string => {
    // Generates a client-side JWT payload matching backend HS256 / Supabase tokens
    const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
    const payload = btoa(JSON.stringify({
      sub: user.id,
      email: user.email,
      role: user.role,
      name: user.name,
      facility_id: user.facility_id,
      patient_id: user.patient_id,
      exp: Math.floor(Date.now() / 1000) + (86400 * 7)
    }));
    return `${header}.${payload}.mock_sig`;
  };

  useEffect(() => {
    setToken(generateDemoToken(currentUser));
  }, [currentUser]);

  const switchRole = (role: UserRole) => {
    setCurrentUser(DEMO_USERS[role]);
  };

  return (
    <AuthContext.Provider value={{ currentUser, switchRole, token }}>
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
