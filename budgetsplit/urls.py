"""
Main URL configuration for the budgetsplit project.

Each app owns its own urls.py (included with a namespace below), so
individual apps stay self-contained and reusable -- this file is just
the top-level router tying them together.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('budgets/', include('budgets.urls', namespace='budgets')),
    path('groups/', include('groups.urls', namespace='groups')),

    # Root URL: send logged-in users straight to their dashboard;
    # anonymous visitors get redirected into the login flow, which in
    # turn will bounce them to the dashboard after a successful login.
    path('', login_required(RedirectView.as_view(pattern_name='accounts:dashboard'), login_url='accounts:login'), name='home'),
]

# Serve user-uploaded media files (avatars) during local development.
# In production, a real web server or WhiteNoise-style setup handles
# this instead -- Django's own dev-only static serving is never used
# for MEDIA in a real deployment.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
