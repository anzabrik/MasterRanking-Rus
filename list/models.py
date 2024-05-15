from django.db import models
from django.contrib.auth.models import AbstractUser
from django.urls import reverse
import datetime
from django.template.defaultfilters import slugify
from django.utils.text import slugify

class User(AbstractUser):

    def __str__(self):
        return f"{self.username}"


class Master(models.Model):
    name = models.CharField(max_length=960)
    time = models.DateTimeField(auto_now_add=True, null=True)
    slug = models.SlugField(max_length=250, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:        
        constraints = [
            models.UniqueConstraint(fields=['name', 'user'], name='У пользователя не должно быть несколько МастерРэнкингов с одним названием'),
            models.UniqueConstraint(fields=['slug', 'user'], name='Слаг для МастерРэнкинга должен быть уникальным')
        ]  

    '''
    Related:
    list
    book_in_master
    author_in_master
    '''
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('master', kwargs={'master_id': self.id, 'slug': self.slug})
    
    def save(self, *args, **kwargs):
        self.slug = slugify(self.name, allow_unicode=True)
        super(Master, self).save(*args, **kwargs)


class List(models.Model):
    name = models.CharField(max_length=320)
    info = models.CharField(max_length=960, blank=True)
    url = models.URLField(max_length=560, blank=True)
    credibility = models.PositiveIntegerField(default=3)
    # First, it's number user typed in "add list" form, not actual book count, then reset 
    book_num = models.PositiveIntegerField(default=10) 
    masters = models.ManyToManyField(Master, blank=True)
    places_matter = models.BooleanField()
    slug = models.SlugField(max_length=250, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:        
        constraints = [
            models.UniqueConstraint(fields=['name', 'user'], name='У пользователя не дожно быть несколько списков с одним названием'),
            models.UniqueConstraint(fields=['slug', 'user'], name='Слаг для списка должен быть уникальным')
        ]  

    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('list', kwargs={'list_id': self.id, 'slug': self.slug})
    
    def save(self, *args, **kwargs):
        self.slug = slugify(self.name, allow_unicode=True)
        super(List, self).save(*args, **kwargs)


class Author(models.Model):
    name = models.CharField(max_length=800) 
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:        
        constraints = [
            models.UniqueConstraint(fields=['name', 'user'], name='Пользователь может создать только одного автора с этим именем'),
        ] 

    def __str__(self):
        return self.name  
    
    def get_books(self):
        if self.book_set.count() == 1:
            return self.book_set.first()
        else:
            books_by_author = ""
            for book in self.book_set.all():
                books_by_author += f"{book.title}<br>"
            return books_by_author
 
class Book(models.Model):
    title = models.CharField(max_length=320)
    authors = models.ManyToManyField(Author, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    class Meta:        
        constraints = [
            models.UniqueConstraint(fields=['title', 'user'], name='Пользователь может создать только одну книгу с этим именем'),
        ]  

    def __str__(self):
        return self.title

    def get_info(self):
        pass

    def get_authors(self):
        if self.authors.count() == 0:
            return ""
        elif self.authors.count() == 1:
            return self.authors.first()
        else:
            authors = ""
            for author in self.authors.all():
                authors += f"{author}, "
            return authors[:-2]
    

class Book_In_List(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE) #if book deleted, bil is deleted too
    list = models.ForeignKey(List, on_delete=models.CASCADE)
    info = models.CharField(max_length=960, blank=True)
    place = models.PositiveIntegerField(default=1)
    rating = models.PositiveIntegerField(default=0)
    atom_count = models.PositiveIntegerField(default=0)
    
    class Meta:        
        constraints = [
            models.UniqueConstraint(fields=['book', 'list'], name='книга один раз в списке')
        ]  
    
    def __str__(self):
        if self.place == 0:
            return f"{self.list}: {self.book.title}"
        return f"{self.list}, place {self.place}, {self.atom_count}: {self.book.title}"


class Author_In_List(models.Model):  
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    list = models.ForeignKey(List, on_delete=models.CASCADE)
    rating = models.PositiveIntegerField(default=0)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['author', 'list'], name='автор один раз в списке')
        ]   

    def __str__(self):
        return f"{self.list}: {self.author.name}"
    

class Book_In_Master(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    master = models.ForeignKey(Master, on_delete=models.CASCADE)
    rating = models.IntegerField(default=0)
    place = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.master}: {self.book}"
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['book', 'master'], name='книга один раз в МастерРэнкинге')
        ]


class Author_In_Master(models.Model):
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    master = models.ForeignKey(Master, on_delete=models.CASCADE)
    rating = models.IntegerField(default=0)
    place = models.IntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['author', 'master'], name='автор один раз в МастерРэнкинге')
        ]

    def get_books(self):
        if self.author.book_set.count() == 1:
            return self.author.book_set.first()
        else:
            books_by_author_in_this_master = ""
            for bim in Book_In_Master.objects.filter(master=self.master):
                for book in self.author.book_set.all():
                    if book.title == bim.book.title:
                        books_by_author_in_this_master += f"{bim.book.title}, "
            return books_by_author_in_this_master[:-2]
    
    def __str__(self):
        return f"{self.master}: {self.author}"