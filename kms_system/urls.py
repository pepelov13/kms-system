from django.contrib import admin
from django.conf import settings
from django.urls import path, include
from django.views.generic import RedirectView
from django.contrib.auth import views as auth_views
from users.views import RoleBasedLoginView, employee_dashboard, manager_dashboard

urlpatterns = [
    # Admin Panel
    path('admin/', admin.site.urls),

    # Authentication
    path('accounts/', include([
        path('login/', RoleBasedLoginView.as_view(), name='login'),
        path('logout/', auth_views.LogoutView.as_view(template_name='registration/logged_out.html'), name='logout'),
        path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
        path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
        path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
        path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    ])),

    # Dashboards
    path('employee/dashboard/', employee_dashboard, name='employee_dashboard'),
    path('manager/dashboard/', manager_dashboard, name='manager_dashboard'),

    # Assessment App (now includes start_assessment and assignment logic)
    path('assessments/', include('assessments.urls', namespace='assessments')),
 
    # Results App
    path('results/', include(('results.urls', 'results'), namespace='results')),

    # Default Redirect
    path('', RedirectView.as_view(pattern_name='login', permanent=False)),
]

# Debug Toolbar
if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns