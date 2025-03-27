from django.db import models

class TyreScan(models.Model):
    image = models.CharField(max_length=255)  # Stored as string path (e.g., "tyres/xyz.jpg")
    result = models.CharField(max_length=20)
    scanned_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.result} | {self.image}"
