from api.user.models import User
from django.db import models
from lib.core.models import BaseModel


class Aspiration(BaseModel):
    """
    Aspiration/ or saving goal ideas
    """
    title = models.CharField(max_length=300)
    description = models.TextField()
    short_description = models.CharField(max_length=100, default='')
    icon_image = models.ImageField(max_length=500, upload_to='aspirations')
    image = models.ImageField(max_length=500, upload_to='aspirations')
    appreciation = models.IntegerField(default=0)
    follower = models.IntegerField(default=0)
    target_amount = models.DecimalField(max_digits=8, decimal_places=2, help_text="Amount to be save", default=0)
    target_date = models.DateTimeField(null=True, blank=True, help_text='Specific date of an event or festival')
    target_days = models.SmallIntegerField(default=0, help_text="No's of days to complete this goals")
    completed = models.IntegerField(default=0)
    in_progress = models.IntegerField(default=0)

    featured = models.BooleanField(default=False, help_text='Featured aspiration will be shown on top or home page as '
                                                            'per the requirements')

    def __str__(self):
        return self.title

    def follow(self, user):
        aspiration, status = AspirationFollower.objects.get_or_create(user=user, aspiration=self)


class AspirationFollower(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    aspiration = models.ForeignKey(Aspiration, on_delete=models.CASCADE)

    def __str__(self):
        return F"{self.aspiration.title}, {self.user.get_full_name()}"