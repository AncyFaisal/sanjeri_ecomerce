from django.db import models

# Create your models here.
class Auther(models.Model):
    name=models.CharField(max_length=100)
    age=models.IntegerField()

class Book(models.Model):
    book_name=models.CharField(max_length=100)
    published_date=models.DateField()
    author=models.ForeignKey(Auther,on_delete=models.CASCADE, related_name="author")
class Library(models.Model):
    lib_name=models.CharField(max_length=100)
    books=models.ManyToManyField(Book,related_name="books")
                                 
