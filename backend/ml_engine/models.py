from django.db import models

class UniversityMajor(models.Model):
    GENERIC_MAJORS = [
        ('Agriculture', 'Agriculture'),
        ('Architecture', 'Architecture'),
        ('Arts', 'Arts'),
        ('Business', 'Business'),
        ('Education', 'Education'),
        ('Finance', 'Finance'),
        ('Government', 'Government'),
        ('Health', 'Health'),
        ('Hospitality', 'Hospitality'),
        ('Human Services', 'Human Services'),
        ('IT', 'IT'),
        ('Law', 'Law'),
        ('Manufacturing', 'Manufacturing'),
        ('Sales', 'Sales'),
        ('Science', 'Science'),
        ('Transport', 'Transport'),
    ]
    
    ml_category = models.CharField(max_length=50, choices=GENERIC_MAJORS, help_text="The generic field predicted by the AI (e.g., IT, Business).")
    official_name = models.CharField(max_length=200, help_text="The exact official course name offered by your university.")
    
    class Meta:
        verbose_name = "University Major Mapping"
        verbose_name_plural = "University Major Mappings"
        ordering = ['ml_category', 'official_name']

    def __str__(self):
        return f"{self.ml_category} -> {self.official_name}"

class CareerPath(models.Model):
    university_major = models.ForeignKey(UniversityMajor, on_delete=models.CASCADE, related_name='career_paths', help_text="The specific university program this career belongs to.")
    job_title = models.CharField(max_length=200, help_text="A potential job or career path (e.g., Software Engineer).")

    class Meta:
        verbose_name = "Career Path Mapping"
        verbose_name_plural = "Career Path Mappings"
        ordering = ['university_major', 'job_title']

    def __str__(self):
        return f"{self.university_major.official_name} -> {self.job_title}"
