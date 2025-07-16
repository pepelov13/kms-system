from django.urls import path
from . import views

app_name = 'results'

urlpatterns = [
    path('employee/', views.employee_results, name='employee_results'),
    path('manager/', views.manager_results, name='manager_results'),
    path('employee/<int:employee_id>/assessment/<int:assessment_id>/', views.view_employee_results, name='view_employee_results'),
    path('submit/<int:assessment_id>/', views.submit_assessment, name='submit_assessment'),
    path('complete/<int:assessment_id>/', views.assessment_complete, name='assessment_complete'),
    path('export/csv/', views.export_results_csv, name='export_results_csv'),
    path('certificate/<int:result_id>/', views.generate_certificate_pdf, name='generate_certificate'),
]
