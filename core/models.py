from django.db import models

class SoftDeleteQuerySet(models.QuerySet):
    def delete(self):
        # Perform soft delete by setting is_deleted=True
        return self.update(is_deleted=True)

class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        # Exclude soft deleted records by default
        return SoftDeleteQuerySet(self.model, using=self._db).filter(is_deleted=False)

class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    # Managers
    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        # Soft delete the individual record
        self.is_deleted = True
        self.save(update_fields=['is_deleted', 'updated_at'])
