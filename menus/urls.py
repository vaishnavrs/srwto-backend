from .views import  dscr_calculate,dscr_pdf_table
from django.urls import path,include

urlpatterns = [
    path('dscr/',dscr_calculate),
    path('dscr_exact/',dscr_pdf_table)
    
]