from django.urls import path
from movies.api.v1 import views

urlpatterns = [
    path('info/', views.project_info),
    path('movies/', views.MoviesListApi.as_view()),
    path('movies/<uuid:pk>/', views.MoviesDetailApi.as_view()),
]
