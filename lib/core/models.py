import uuid as uuid
from django.db import models
from django.db.models import Manager, QuerySet
from django.utils import timezone


class DefaultQuerySet(QuerySet):
    pass


class DefaultManager(Manager):
    def get_queryset(self):
        return DefaultQuerySet(self.model).filter(deleted_at=None)

    def delete(self, queryset):
        return DefaultQuerySet(self.model).update(deleted_at=timezone.now())


class BaseModel(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, blank=True)
    deleted_at = models.DateTimeField(default=None, null=True, blank=True)

    objects = DefaultManager()
    all_objects = Manager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False, hard_delete=False):
        if not hard_delete:
            self.deleted_at = timezone.now()
            self.save()
        else:
            super(BaseModel,self).delete(using=using, keep_parents=keep_parents)