# models/category.py
from django.db import models
from django.utils import timezone

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=255, null=True, blank=True)
    thumbnail = models.ImageField(upload_to='category_thumbnails/', blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    
    # Visibility & Marketing
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=0)

    # Soft delete
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True, default=None)

   
    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"

    # def soft_delete(self):
    #     """Soft delete the category"""
    #     self.is_active = False
    #     self.is_deleted = True
    #     self.deleted_at = timezone.now()
    #     self.save()

    # def restore(self):
    #     """Restore soft deleted category"""
    #     self.is_active = True
    #     self.is_deleted = False
    #     self.deleted_at = None
    #     self.save()

    # def permanent_delete(self):
    #     """Permanently delete the category"""
    #     super().delete()

    # # ✅ ADD CUSTOM MANAGERS
    # # Default manager - shows only non-deleted categories
    # objects = models.Manager()
    
    # # Manager that includes all categories (including deleted)
    # class AllCategoriesManager(models.Manager):
    #     def get_queryset(self):
    #         return super().get_queryset()
    
    # all_objects = AllCategoriesManager()