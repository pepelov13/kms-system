from django.urls import path
from . import views

app_name = 'assessments'  # Namespace for use in templates (e.g. {% url 'assessments:start_assessment' %})

urlpatterns = [
    # Dashboard & List Views
    path('', views.assessment_dashboard, name='assessment_dashboard'),
    path('list/', views.assessment_dashboard, name='assessment_list'),

    # --- Assessment Creation (Step-by-step) ---
    path('create/', views.create_assessment, name='create_assessment'),
    path('<int:assessment_id>/question/<int:step>/', views.add_question, name='add_question'),
    path('<int:assessment_id>/overview/', views.assessment_overview, name='assessment_overview'),
    path('question/<int:question_id>/edit/', views.edit_question, name='edit_question'),
    path('question/<int:question_id>/delete/', views.delete_question, name='delete_question'),

    # Assessment Editing
    path('<int:assessment_id>/edit/', views.edit_assessment, name='edit_assessment'),
    path('<int:assessment_id>/delete/', views.delete_assessment, name='delete_assessment'),
    path('<int:assessment_id>/', views.assessment_detail, name='assessment_detail'),

    # Assignment & Taking
    path('assign/', views.assign_assessment, name='assign_assessment'),
    path('start/<int:assessment_id>/', views.start_assessment, name='start_assessment'),
    path('continue/<int:assessment_id>/', views.continue_assessment, name='continue_assessment'),

    # Completion & Results
    
    path('results/', views.manager_results, name='manager_results'),
]