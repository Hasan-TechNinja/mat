import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mat.settings")

import django
django.setup()

from rest_framework.test import APIRequestFactory
from authentication.views import SocialAuthView

factory = APIRequestFactory()
request = factory.post('/social-auth/', {
    'email': 'newuser1@example.com',
    'first_name': 'New',
    'last_name': 'User',
})

view = SocialAuthView.as_view()
try:
    response = view(request)
    print("Response status:", response.status_code)
except Exception as e:
    import traceback
    traceback.print_exc()

