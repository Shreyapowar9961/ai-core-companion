import { initializeApp, getApps, getApp } from 'firebase/app';
import { getMessaging, getToken, onMessage, isSupported, Messaging } from 'firebase/messaging';
import { apiClient } from '../api/client';

// Public Firebase Web Client Configuration
const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
};

const VAPID_KEY = import.meta.env.VITE_FIREBASE_VAPID_KEY;

let messagingInstance: Messaging | null = null;

export const isPushSupported = async (): Promise<boolean> => {
  if (typeof window === 'undefined') return false;
  if (!('serviceWorker' in navigator) || !('Notification' in window)) return false;
  try {
    return await isSupported();
  } catch (err) {
    console.warn('FCM browser support check failed:', err);
    return false;
  }
};

export const getNotificationPermission = (): NotificationPermission | 'unsupported' => {
  if (typeof window === 'undefined' || !('Notification' in window)) {
    return 'unsupported';
  }
  return Notification.permission;
};

export const initFirebaseMessaging = async (): Promise<Messaging | null> => {
  if (messagingInstance) return messagingInstance;
  const supported = await isPushSupported();
  if (!supported) return null;

  try {
    const app = getApps().length ? getApp() : initializeApp(firebaseConfig);
    messagingInstance = getMessaging(app);
    return messagingInstance;
  } catch (err) {
    console.warn('Failed to initialize Firebase Messaging:', err);
    return null;
  }
};

/**
 * Registers the background service worker passing public client configuration via query params.
 */
const registerServiceWorker = async (): Promise<ServiceWorkerRegistration | null> => {
  if (!('serviceWorker' in navigator)) return null;

  const queryParams = new URLSearchParams({
    apiKey: firebaseConfig.apiKey || '',
    authDomain: firebaseConfig.authDomain || '',
    projectId: firebaseConfig.projectId || '',
    storageBucket: firebaseConfig.storageBucket || '',
    messagingSenderId: firebaseConfig.messagingSenderId || '',
    appId: firebaseConfig.appId || '',
  });

  const swUrl = `/firebase-messaging-sw.js?${queryParams.toString()}`;

  try {
    const registration = await navigator.serviceWorker.register(swUrl, { scope: '/' });
    await navigator.serviceWorker.ready;
    return registration;
  } catch (err) {
    console.error('Service worker registration error:', err);
    return null;
  }
};

/**
 * Explicit patient-initiated permission request and device registration.
 * NEVER invoked automatically without user interaction.
 */
export const requestPushPermissionAndGetToken = async (
  authToken: string
): Promise<{ success: boolean; token?: string; error?: string }> => {
  const supported = await isPushSupported();
  if (!supported) {
    return { success: false, error: 'Push notifications are not supported in this browser.' };
  }

  if (!VAPID_KEY) {
    return { success: false, error: 'Firebase public VAPID key is not configured.' };
  }

  try {
    const permission = await Notification.requestPermission();
    if (permission !== 'granted') {
      return { success: false, error: `Notification permission ${permission}.` };
    }

    const messaging = await initFirebaseMessaging();
    if (!messaging) {
      return { success: false, error: 'Could not initialize messaging instance.' };
    }

    const swReg = await registerServiceWorker();
    if (!swReg) {
      return { success: false, error: 'Could not register background service worker.' };
    }

    const token = await getToken(messaging, {
      vapidKey: VAPID_KEY,
      serviceWorkerRegistration: swReg,
    });

    if (!token) {
      return { success: false, error: 'No FCM registration token received.' };
    }

    // Register token with backend PostgreSQL storage
    await apiClient.registerDeviceToken(authToken, {
      fcm_token: token,
      device_type: 'web',
      user_agent: navigator.userAgent.slice(0, 250),
    });

    localStorage.setItem('fcm_token_registered', 'true');
    return { success: true, token };
  } catch (err: any) {
    console.error('Error enabling push notifications:', err);
    return { success: false, error: err?.message || 'Failed to enable push notifications.' };
  }
};

/**
 * Opt-out and deregister push token.
 */
export const deregisterPushToken = async (
  authToken: string
): Promise<{ success: boolean; error?: string }> => {
  try {
    await apiClient.unregisterDeviceToken(authToken);
    localStorage.removeItem('fcm_token_registered');
    return { success: true };
  } catch (err: any) {
    console.error('Error deregistering push token:', err);
    return { success: false, error: err?.message || 'Failed to deregister push token.' };
  }
};

/**
 * Listen for foreground push messages while the patient portal is open.
 */
export const setupForegroundPushListener = async (
  onMessageReceived: (payload: any) => void
): Promise<(() => void) | null> => {
  const messaging = await initFirebaseMessaging();
  if (!messaging) return null;

  try {
    const unsubscribe = onMessage(messaging, (payload) => {
      onMessageReceived(payload);
    });
    return unsubscribe;
  } catch (err) {
    console.warn('Failed to attach foreground message listener:', err);
    return null;
  }
};
