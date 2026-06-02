import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';

interface OnboardingGuardProps {
  children: React.ReactNode;
  requireAdmin?: boolean;
}

const OnboardingGuard: React.FC<OnboardingGuardProps> = ({ children, requireAdmin = false }) => {
  const location = useLocation();
  
  // Get fresh auth status from localStorage
  const isAuthenticated = !!localStorage.getItem('access_token');
  const userRole = localStorage.getItem('user_role');
  const hasCompletedSociodemographic = localStorage.getItem('has_completed_sociodemographic') === 'true';

  if (!isAuthenticated) {
    // Redirect to login but save the current location they were trying to access
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Admin Exception: Admins can bypass baseline requirements for management
  if (userRole === 'Admin') {
    return <>{children}</>;
  }

  if (requireAdmin && userRole !== 'Admin') {
    return <Navigate to="/dashboard" replace />;
  }

  // Participant Redirection Logic
  if (!hasCompletedSociodemographic) {
    // allow access to /sociodemographic AND active questionnaire IDs
    const isAllowedPath = location.pathname === '/sociodemographic' || 
                         location.pathname.startsWith('/questionnaire/');
                         
    if (!isAllowedPath) {
      return <Navigate to="/sociodemographic" replace />;
    }
  } else {
    // If they HAVE finished onboarding, they shouldn't be on the onboarding pages anymore
    if (location.pathname === '/sociodemographic') {
      return <Navigate to="/dashboard" replace />;
    }
  }

  return <>{children}</>;
};

export default OnboardingGuard;
