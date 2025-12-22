from django.db import models

class HomeCategory(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

class HomeBrand(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

class HomeProduct(models.Model):
    name = models.CharField(max_length=200)
    category = models.ForeignKey(HomeCategory, on_delete=models.CASCADE)
    brand = models.ForeignKey(HomeBrand, on_delete=models.CASCADE)
    fragrance_family = models.CharField(max_length=50)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    image = models.ImageField(upload_to='products/')
    created_at = models.DateTimeField(auto_now_add=True)
    popularity = models.PositiveIntegerField(default=0)

    def discounted_price(self):
        if self.discount:
            return self.price - self.discount
        return self.price

    def __str__(self):
        return self.name

class HomeRating(models.Model):
    product = models.ForeignKey(HomeProduct, on_delete=models.CASCADE, related_name='ratings')
    rating = models.PositiveSmallIntegerField(default=0)
