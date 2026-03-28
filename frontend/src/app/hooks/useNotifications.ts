import { useCallback, useMemo, useState } from "react";

import { DEFAULT_NOTIFICATIONS } from "../constants";
import { NOTIFICATIONS_STORAGE_KEY } from "../constants";
import type {
  NotificationCategory,
  NotificationItem,
  ToastTone,
} from "../types";
import { usePersistentState } from "./usePersistentState";

function getInitialNotifications(): NotificationItem[] {
  const saved = window.localStorage.getItem(NOTIFICATIONS_STORAGE_KEY);
  if (!saved) return DEFAULT_NOTIFICATIONS;

  try {
    const parsed = JSON.parse(saved) as NotificationItem[];
    if (Array.isArray(parsed)) {
      return parsed;
    }
    return DEFAULT_NOTIFICATIONS;
  } catch {
    return DEFAULT_NOTIFICATIONS;
  }
}

interface UseNotificationsOptions {
  pushToast: (message: string, tone?: ToastTone) => void;
}

export function useNotifications(options: UseNotificationsOptions) {
  const [notifications, setNotifications] = usePersistentState<NotificationItem[]>(
    NOTIFICATIONS_STORAGE_KEY,
    getInitialNotifications
  );
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [notificationFilter, setNotificationFilter] = useState<"all" | NotificationCategory>("all");

  const unreadCount = useMemo(
    () => notifications.filter((notification) => !notification.read).length,
    [notifications]
  );

  const filteredNotifications = useMemo(
    () =>
      notifications.filter(
        (notification) =>
          notificationFilter === "all" || notification.category === notificationFilter
      ),
    [notificationFilter, notifications]
  );

  const markAllNotificationsRead = useCallback(() => {
    setNotifications((current) => current.map((notification) => ({ ...notification, read: true })));
    options.pushToast("All notifications marked as read", "success");
  }, [options, setNotifications]);

  const markNotificationRead = useCallback(
    (id: string) => {
      setNotifications((current) =>
        current.map((notification) =>
          notification.id === id ? { ...notification, read: true } : notification
        )
      );
      options.pushToast("Notification marked as read", "success");
    },
    [options, setNotifications]
  );

  const dismissNotification = useCallback(
    (id: string) => {
      setNotifications((current) => current.filter((notification) => notification.id !== id));
      options.pushToast("Notification dismissed", "info");
    },
    [options, setNotifications]
  );

  const createNotification = useCallback(
    (notification: Omit<NotificationItem, "id" | "timestamp" | "read">) => {
      const entry: NotificationItem = {
        ...notification,
        id: `notif-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        timestamp: new Date().toISOString(),
        read: false,
      };

      setNotifications((current) => [entry, ...current].slice(0, 30));
      options.pushToast(notification.title, notification.severity === "high" ? "warning" : "info");
    },
    [options, setNotifications]
  );

  return {
    notifications,
    notificationsOpen,
    setNotificationsOpen,
    notificationFilter,
    setNotificationFilter,
    unreadCount,
    filteredNotifications,
    markAllNotificationsRead,
    markNotificationRead,
    dismissNotification,
    createNotification,
  };
}
