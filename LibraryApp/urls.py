from django.urls import path
from . import views


urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('watch/<int:course_id>/<int:video_order>/', views.watch_video, name='watch_video'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.login_view), # Redirect root to login
    path('signup/', views.signup_view, name='signup'),
    path('video/stream/<int:video_id>/', views.serve_video, name='serve_video'),
    
    # Add this line for course enrollment:
    path('enroll/<int:course_id>/', views.enroll_course, name='enroll_course'),
    path('add/', views.add_course, name='add_course'),
    path('unenroll/<int:course_id>/', views.unenroll_course, name='unenroll_course'),
]