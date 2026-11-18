// AI Care Companion - Firebase Cloud Messaging Web Push Service Worker
// Strictly ₹0 budget / Free tier compliant
// Never embeds private service account secrets or PHI

importScripts('https://www.gstatic.com/firebasejs/10.12.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.12.0/firebase-messaging-compat.js');

// Parse public config passed during registration via query params
const swUrl = new URL(location.href);
const apiKey = swUrl.searchParams.get('apiKey') || '';
const authDomain = swUrl.searchParams.get('authDomain') || '';
const projectId = swUrl.searchParams.get('projectId') || 'ai-care-companion-5df51';
const storageBucket = swUrl.searchParams.get('storageBucket') || '';
const messagingSenderId = swUrl.searchParams.get('messagingSenderId') || '';
const appId = swUrl.searchParams.get('appId') || '';

if (apiKey && projectId) {
  try {
    firebase.initializeApp({
      apiKey: apiKey,
      authDomain: authDomain,
      projectId: projectId,
      storageBucket: storageBucket,
      messagingSenderId: messagingSenderId,
      appId: appId
    });

    const messaging = firebase.messaging();

    messaging.onBackgroundMessage((payload) => {
      // Strictly generic, privacy-safe notification display
      const notificationTitle = payload.notification?.title || payload.data?.title || 'AI Care Companion';
      const notificationOptions = {
        body: payload.notification?.body || payload.data?.body || 'You have a new recovery reminder. Open your patient portal.',
        icon: '/vite.svg',
        badge: '/vite.svg',
        tag: 'ai-care-companion-recovery-reminder',
        renotify: true,
        data: {
          click_action: payload.data?.click_action || '/portal',
          timestamp: Date.now()
        }
      };

      return self.registration.showNotification(notificationTitle, notificationOptions);
    });
  } catch (err) {
    console.warn('[firebase-messaging-sw.js] Initialization warning:', err);
  }
}

// Handle notification click: focus existing window or open /portal
self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  const clickAction = event.notification.data?.click_action || '/portal';

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      for (const client of clientList) {
        if (client.url.includes('/portal') && 'focus' in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(clickAction);
      }
    })
  );
});
