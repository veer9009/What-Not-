export const notificationChanged='what-not-notifications-changed';
export function refreshNotificationCount(){window.dispatchEvent(new Event(notificationChanged));}
