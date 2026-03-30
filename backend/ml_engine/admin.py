from django.contrib import admin
from .models import UniversityMajor, CareerPath

@admin.register(UniversityMajor)
class UniversityMajorAdmin(admin.ModelAdmin):
    list_display = ('official_name', 'ml_category')
    list_filter = ('ml_category',)
    search_fields = ('official_name', 'ml_category')

@admin.register(CareerPath)
class CareerPathAdmin(admin.ModelAdmin):
    list_display = ('job_title', 'university_major')
    list_filter = ('university_major__ml_category',)
    search_fields = ('job_title', 'university_major__official_name')
