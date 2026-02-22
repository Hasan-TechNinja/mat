import os
import logging
import firebase_admin
from firebase_admin import credentials, messaging
from django.conf import settings

logger = logging.getLogger(__name__)

def initialize_firebase():
    """Initializes Firebase Admin SDK if not already initialized."""
    if not firebase_admin._apps:
        service_account_path = getattr(settings, 'FIREBASE_SERVICE_ACCOUNT_PATH', None)
        print(f"[FCM] Initializing Firebase with: {service_account_path}")
        
        if service_account_path and os.path.exists(service_account_path):
            try:
                cred = credentials.Certificate(service_account_path)
                firebase_admin.initialize_app(cred)
                print("[FCM] Firebase Admin SDK initialized successfully.")
            except Exception as e:
                print(f"[FCM] Error initializing Firebase Admin SDK: {e}")
        else:
            print(f"[FCM] Firebase service account file not found at {service_account_path}.")
    else:
        print("[FCM] Firebase already initialized.")

def send_push_notification(user, title, body, data=None):
    """
    Sends a push notification to all active devices of a user.
    """
    print(f"[FCM] send_push_notification called for user={user.username}, title={title}")
    initialize_firebase()
    
    from .models import DeviceToken
    from .models import Notification
    tokens = list(DeviceToken.objects.filter(user=user, is_active=True).values_list('token', flat=True))
    print(f"[FCM] Found {len(tokens)} active device tokens for user {user.username}")
    
    if not tokens:
        print(f"[FCM] No active device tokens. Creating DB notification only.")
        try:
            Notification.objects.create(user=user, title=title, body=body)
            print(f"[FCM] Notification record created in DB.")
        except Exception as e:
            print(f"[FCM] Failed to create Notification record: {e}")
        return

    if not firebase_admin._apps:
        print(f"[FCM] MOCK MODE - Firebase not initialized. Logging notification.")
        try:
            Notification.objects.create(user=user, title=title, body=body)
            print(f"[FCM] Notification record created in DB (MOCK mode).")
        except Exception as e:
            print(f"[FCM] Failed to create Notification record in MOCK mode: {e}")
        return

    print(f"[FCM] Sending push to {len(tokens)} device(s)...")
    message = messaging.MulticastMessage(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        data=data or {},
        tokens=tokens,
    )

    try:
        response = messaging.send_each_for_multicast(message)
        print(f"[FCM] Push result: {response.success_count} success, {response.failure_count} failed.")
        
        if response.failure_count > 0:
            for idx, resp in enumerate(response.responses):
                if not resp.success:
                    invalid_token = tokens[idx]
                    DeviceToken.objects.filter(token=invalid_token).update(is_active=False)
                    print(f"[FCM] Deactivated invalid token: {invalid_token[:10]}...")
                    
    except Exception as e:
        print(f"[FCM] Error sending push notification: {e}")
    finally:
        try:
            Notification.objects.create(user=user, title=title, body=body)
            print(f"[FCM] Notification record created in DB.")
        except Exception as e:
            print(f"[FCM] Failed to create Notification record: {e}")
